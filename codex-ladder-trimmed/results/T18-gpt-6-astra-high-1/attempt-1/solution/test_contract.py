import copy
from dataclasses import FrozenInstanceError, fields
import json
import random
import unittest
from unittest.mock import patch

import api
import core
import model
import render
import service


def journal(commands):
    return json.loads(api.run(json.dumps(commands)))


def put(key, cost, **extra):
    return {"op": "put", "key": key, "input": [["s", "t", cost], ["s", "t"]], **extra}


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result_and_exact_json_values(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        for value in [None, 0, 12, True, "é", [None, {"nested": [1, False]}]]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIs(type(result), model.Result)
                self.assertEqual(result.value, value)
                self.assertIsInstance(render.present(result), str)
                self.assertEqual(json.loads(render.present(result)), value)
                with self.assertRaises(FrozenInstanceError):
                    result.value = 5

    def test_shortest_paths(self):
        cases = [
            ([["a", "a"]], 0),
            ([["a", "b"]], None),
            ([["a", "b", 8], ["a", "b", 2], ["b", "c", 3], ["a", "c", 9], ["a", "c"]], 5),
            ([["a", "b", 0], ["b", "a", 0], ["b", "c", 0], ["a", "c"]], 0),
            ([["b", "a", 1], ["a", "b"]], None),
            ([["a", 1, 0], ["a", "b", 0], [1, "z", 7], ["b", "z", 3], ["a", "z"]], 3),
            ([[0, 1, 10 ** 100], [0, 1]], 10 ** 100),
        ]
        for rows, expected in cases:
            original = copy.deepcopy(rows)
            self.assertEqual(core.solve(rows), expected)
            self.assertEqual(service.compute(rows), model.Result(expected))
            self.assertEqual(rows, original)

    def test_random_graphs_against_bellman_ford(self):
        rng = random.Random(7041)
        for _ in range(250):
            count = rng.randrange(1, 10)
            edges = [[rng.randrange(count), rng.randrange(count), rng.randrange(20)]
                     for _ in range(rng.randrange(50))]
            source, target = rng.randrange(count), rng.randrange(count)
            distances = {source: 0}
            for _ in range(count - 1):
                for u, v, weight in edges:
                    if u in distances:
                        candidate = distances[u] + weight
                        if v not in distances or candidate < distances[v]:
                            distances[v] = candidate
            self.assertEqual(core.solve(edges + [[source, target]]), distances.get(target))


class JournalTests(unittest.TestCase):
    def test_empty_and_sorted_unicode_keys(self):
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        keys = ["😀", "é", "z", "", "A"]
        result = journal([put(key, i) for i, key in enumerate(keys)] + [{"op": "list"}])
        expected = sorted([[key, i] for i, key in enumerate(keys)])
        self.assertEqual(result["state"], expected)
        self.assertEqual(result["events"][-1], {"ok": expected})

    def test_get_delete_expect_and_null(self):
        result = journal([
            {"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
            {"op": "expect", "key": "x", "value": None},
            {"op": "put", "key": "x", "input": [["a", "b"]]},
            {"op": "get", "key": "x"}, {"op": "expect", "key": "x", "value": None},
            put("x", 1), {"op": "expect", "key": "x", "value": True},
            {"op": "expect", "key": "x", "value": 2},
            {"op": "delete", "key": "x"}, {"op": "list"},
        ])
        self.assertEqual(result["events"], [
            {"error": "missing"}, {"error": "missing"}, {"error": "expectation"},
            {"ok": None}, {"ok": None}, {"ok": True}, {"ok": 1}, {"ok": True},
            {"error": "expectation"}, {"ok": 1}, {"ok": []},
        ])
        self.assertEqual(result["state"], [])

    def test_nested_savepoints_and_no_implicit_rollback(self):
        result = journal([
            {"op": "commit"}, {"op": "rollback"}, put("x", 1),
            {"op": "begin"}, put("x", 2), {"op": "begin"}, put("x", 3),
            {"op": "expect", "key": "x", "value": 99}, {"op": "get", "key": "x"},
            {"op": "rollback"}, {"op": "get", "key": "x"},
            {"op": "begin"}, {"op": "delete", "key": "x"}, {"op": "commit"},
            {"op": "list"}, {"op": "rollback"}, {"op": "get", "key": "x"},
        ])
        self.assertEqual(result["events"], [
            {"error": "transaction"}, {"error": "transaction"}, {"ok": 1},
            {"ok": 1}, {"ok": 2}, {"ok": 2}, {"ok": 3},
            {"error": "expectation"}, {"ok": 3}, {"ok": 1}, {"ok": 2},
            {"ok": 2}, {"ok": 2}, {"ok": 1}, {"ok": []}, {"ok": 0}, {"ok": 1},
        ])
        self.assertEqual(result["state"], [["x", 1]])
        self.assertEqual(result["depth"], 0)

    def test_malformed_commands_are_atomic(self):
        bad = [None, [], 7, "put", {}, {"op": []}, {"op": {}}, {"op": None},
               {"op": "unknown"}, {"op": "put", "key": "x"},
               {"op": "put", "input": []}, {"op": "get"}, {"op": "delete"},
               {"op": "expect", "key": "x"}, {"op": "expect", "value": 1}]
        for op in ["put", "get", "delete", "expect"]:
            for key in [None, 3, False, [], {}]:
                bad.append({"op": op, "key": key, "input": [], "value": 1})
        for op in ["begin", "commit", "rollback", "list"]:
            for identifier in [None, 3, False, [], {}]:
                bad.append({"op": op, "id": identifier})
        result = journal([put("x", 4), {"op": "begin"}] + bad + [{"op": "get", "key": "x"}])
        self.assertEqual(result["events"][2:-1], [{"error": "command"}] * len(bad))
        self.assertEqual(result["events"][-1], {"ok": 4})
        self.assertEqual(result["state"], [["x", 4]])
        self.assertEqual(result["depth"], 1)

    def test_cache_precedes_validation_and_identity_includes_extras(self):
        command = put("x", 1, id="", extra={"a": [1, None], "b": 2})
        replay = dict(reversed(list(command.items())))
        replay["extra"] = {"b": 2.0, "a": [True, None]}
        changed = {**command, "extra": {"a": [2, None], "b": 2}}
        result = journal([command, {"op": "delete", "key": "x"}, replay, changed,
                          {"op": [], "id": ""}, {"id": ""}, {"op": "get", "key": "x"}])
        self.assertEqual(result["events"], [
            {"ok": 1}, {"ok": 1}, {"ok": 1}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "id-conflict"}, {"error": "missing"},
        ])
        self.assertEqual(result["state"], [])

    def test_failed_operations_do_not_reserve_ids(self):
        failures = [{"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
                    {"op": "expect", "key": "x", "value": None},
                    {"op": "commit"}, {"op": "rollback"}, {"op": "put", "key": "x"}]
        for failure in failures:
            result = journal([{**failure, "id": "retry"}, put("x", 5, id="retry")])
            self.assertIn("error", result["events"][0])
            self.assertEqual(result["events"][1], {"ok": 5})

    def test_cache_survives_rollback_and_control_replay_has_no_effect(self):
        begin = {"op": "begin", "id": "begin"}
        rollback = {"op": "rollback", "id": "rollback"}
        listing = {"op": "list", "id": "list"}
        commit = {"op": "commit", "id": "commit"}
        saved_put = put("x", 7, id="put")
        result = journal([
            begin, begin, saved_put, listing, rollback, saved_put, listing,
            {"op": "begin"}, put("x", 9), rollback, commit,
            {"op": "begin"}, commit,
        ])
        self.assertEqual(result["events"], [
            {"ok": 1}, {"ok": 1}, {"ok": 7}, {"ok": [["x", 7]]}, {"ok": 0},
            {"ok": 7}, {"ok": [["x", 7]]}, {"ok": 1}, {"ok": 9}, {"ok": 0},
            {"ok": 0}, {"ok": 1}, {"ok": 0},
        ])
        self.assertEqual(result["state"], [["x", 9]])
        self.assertEqual(result["depth"], 1)

    def test_ignored_fields_and_fresh_invocations(self):
        result = journal([{"op": "begin", "key": [], "value": 0},
                          {"op": "list", "key": None, "input": []}])
        self.assertEqual(result["events"], [{"ok": 1}, {"ok": []}])
        journal([put("x", 1, id="shared"), {"op": "begin"}])
        self.assertEqual(journal([put("y", 2, id="shared")]),
                         {"events": [{"ok": 2}], "state": [["y", 2]], "depth": 0})

    def test_mutable_pipeline_values_and_deep_ownership(self):
        value = [{"items": [1]}]
        command = {"op": "put", "key": "x", "input": [["a", "a"]]}
        original = copy.deepcopy(command)
        state, stack = {}, []
        with patch.object(core, "solve", return_value=value):
            event = api._execute(command, state, stack)
            event["ok"][0]["items"].append(2)
            self.assertEqual(state["x"], value)
            api._execute({"op": "begin"}, state, stack)
            state["x"][0]["items"].append(3)
            self.assertEqual(stack[0]["x"], value)
            api._execute({"op": "rollback"}, state, stack)
            listed = api._execute({"op": "list"}, state, stack)
            listed["ok"][0][1][0]["items"].append(4)
            self.assertEqual(state["x"], value)
            result = journal([{**command, "id": "p"}, {"op": "begin"},
                              {"op": "delete", "key": "x"}, {"op": "rollback"},
                              {**command, "id": "p"}])
        self.assertEqual(result["state"], [["x", value]])
        self.assertEqual(result["events"][0], {"ok": value})
        self.assertEqual(result["events"][-1], {"ok": value})
        self.assertEqual(command, original)
        self.assertEqual(value, [{"items": [1]}])


if __name__ == "__main__":
    unittest.main()
