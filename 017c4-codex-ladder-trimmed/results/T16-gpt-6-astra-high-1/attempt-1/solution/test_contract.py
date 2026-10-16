import dataclasses
from copy import deepcopy
import itertools
import json
import unittest
from unittest.mock import patch

import api
import core
import model
import render
import service


def journal(commands):
    return json.loads(api.run(json.dumps(commands)))


def put(key, rows=None, **extra):
    return {"op": "put", "key": key, "input": [] if rows is None else rows, **extra}


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result_and_rendering(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([f.name for f in dataclasses.fields(model.Result)], ["value"])
        result = service.compute([["b", "c"], ["a", "c"]])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, ["a", "b", "c"])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.value = []
        for value in [None, False, True, 0, 1.25, "雪", [], {"x": [1, None]}]:
            with self.subTest(value=value):
                self.assertEqual(json.loads(render.present(model.Result(value))), value)
                with patch.object(core, "solve", return_value=value):
                    self.assertEqual(service.compute([]), model.Result(value))

    def test_algorithm_examples_and_input_ownership(self):
        rows = [["b", "z"], ["a", "z"], ["b", "z"], ["", "雪"]]
        original = deepcopy(rows)
        self.assertEqual(core.solve(rows), ["", "a", "b", "z", "雪"])
        self.assertEqual(rows, original)
        self.assertEqual(core.solve([]), [])
        self.assertIsNone(core.solve([["x", "x"]]))
        self.assertIsNone(core.solve([["a", "b"], ["b", "a"], ["c", "d"]]))
        self.assertEqual(core.solve([["a", "b"], ["z", "c"]]), ["a", "b", "z", "c"])

    def test_all_three_node_graphs_against_permutation_oracle(self):
        possible_edges = list(itertools.product("abc", repeat=2))
        for bits in range(1 << len(possible_edges)):
            edges = [edge for index, edge in enumerate(possible_edges) if bits & (1 << index)]
            nodes = sorted({node for edge in edges for node in edge})
            expected = next(
                (list(order) for order in itertools.permutations(nodes)
                 if all(order.index(a) < order.index(b) for a, b in edges)),
                None,
            )
            self.assertEqual(core.solve(edges + edges), expected, edges)


class JournalTests(unittest.TestCase):
    def test_basic_operations_and_unicode_order(self):
        commands = [
            put("雪", [["b", "c"], ["a", "c"]]), put(""),
            put("a", [["x", "x"]]), {"op": "get", "key": "a"},
            {"op": "expect", "key": "a", "value": None},
            {"op": "expect", "key": "missing", "value": None},
            {"op": "list"}, {"op": "delete", "key": "雪"},
            {"op": "get", "key": "雪"}, {"op": "delete", "key": "雪"},
        ]
        original = deepcopy(commands)
        result = journal(commands)
        self.assertEqual(result, {
            "events": [
                {"ok": ["a", "b", "c"]}, {"ok": []}, {"ok": None}, {"ok": None},
                {"ok": True}, {"error": "expectation"},
                {"ok": [["", []], ["a", None], ["雪", ["a", "b", "c"]]]},
                {"ok": ["a", "b", "c"]}, {"error": "missing"}, {"error": "missing"},
            ], "state": [["", []], ["a", None]], "depth": 0,
        })
        self.assertEqual(commands, original)

    def test_nested_savepoints_and_expectation_failure(self):
        result = journal([
            put("x"), {"op": "begin"}, put("x", [["a", "b"]]),
            {"op": "begin"}, {"op": "delete", "key": "x"},
            {"op": "rollback"}, {"op": "expect", "key": "x", "value": []},
            {"op": "commit"}, {"op": "rollback"}, {"op": "commit"}, {"op": "begin"},
        ])
        self.assertEqual(result["events"], [
            {"ok": []}, {"ok": 1}, {"ok": ["a", "b"]}, {"ok": 2},
            {"ok": ["a", "b"]}, {"ok": 1}, {"error": "expectation"},
            {"ok": 0}, {"error": "transaction"}, {"error": "transaction"}, {"ok": 1},
        ])
        self.assertEqual(result["state"], [["x", ["a", "b"]]])
        self.assertEqual(result["depth"], 1)
        self.assertEqual(journal([put("x"), {"op": "begin"}, put("y"),
                                  {"op": "begin"}, put("z"), {"op": "commit"},
                                  {"op": "rollback"}])["state"], [["x", []]])

    def test_invalid_commands_are_atomic_and_do_not_reserve_ids(self):
        malformed = [None, [], 1, "put", {}, {"op": []}, {"op": {}},
                     {"op": "unknown"}, {"op": "put", "key": "x"},
                     {"op": "put", "input": []}, {"op": "get"}, {"op": "delete"},
                     {"op": "expect", "key": "x"}, {"op": "expect", "value": []}]
        for op in ("put", "get", "delete", "expect"):
            for key in (None, 0, False, [], {}):
                malformed.append({"op": op, "key": key, "input": [], "value": []})
        for identifier in (None, 0, False, [], {}):
            malformed.append({"op": "rollback", "id": identifier})
        for bad in malformed:
            with self.subTest(command=bad):
                if isinstance(bad, dict) and "id" not in bad:
                    bad = dict(bad, id="retry")
                result = journal([put("x"), {"op": "begin"}, bad,
                                  {"op": "list", "id": "retry"}, {"op": "rollback"}])
                self.assertEqual(result["events"][2], {"error": "command"})
                self.assertEqual(result["events"][3], {"ok": [["x", []]]})
                self.assertEqual(result["state"], [["x", []]])
                self.assertEqual(result["depth"], 0)

    def test_identity_uses_full_python_equality_and_lookup_precedes_validation(self):
        first = put("", id="", extra={"a": [True, {"b": False}], "z": 1})
        equal = {"extra": {"z": 1.0, "a": [1, {"b": 0}]}, "input": [],
                 "key": "", "id": "", "op": "put"}
        result = journal([first, equal, put("", id=""),
                          {"op": "get", "id": ""}, {"op": [], "id": ""},
                          {"op": "list", "key": 17, "input": None}])
        self.assertEqual(result["events"], [
            {"ok": []}, {"ok": []}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "id-conflict"}, {"ok": [["", []]]},
        ])

    def test_failed_operations_leave_ids_available(self):
        for failed in [{"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
                       {"op": "expect", "key": "x", "value": []},
                       {"op": "commit"}, {"op": "rollback"}]:
            result = journal([dict(failed, id="i"), put("x", id="i")])
            self.assertIn("error", result["events"][0])
            self.assertEqual(result["events"][1], {"ok": []})

    def test_savepoint_replays_and_cache_survives_rollback(self):
        result = journal([
            {"op": "begin", "id": "b"}, {"op": "begin", "id": "b"},
            put("x", id="p"), {"op": "rollback", "id": "r"},
            put("x", id="p"), {"op": "rollback", "id": "r"},
            {"op": "begin", "id": "b"}, {"op": "get", "key": "x"},
        ])
        self.assertEqual(result, {"events": [
            {"ok": 1}, {"ok": 1}, {"ok": []}, {"ok": 0},
            {"ok": []}, {"ok": 0}, {"ok": 1}, {"error": "missing"},
        ], "state": [], "depth": 0})
        self.assertEqual(journal([
            {"op": "begin"}, {"op": "commit", "id": "c"},
            {"op": "begin"}, {"op": "commit", "id": "c"},
        ])["depth"], 1)

    def test_reads_and_delete_replay_original_events(self):
        result = journal([
            put("x"), {"op": "list", "id": "l"}, {"op": "get", "key": "x", "id": "g"},
            {"op": "expect", "key": "x", "value": [], "id": "e"},
            {"op": "delete", "key": "x", "id": "d"}, put("x", [["a", "b"]]),
            {"op": "list", "id": "l"}, {"op": "get", "key": "x", "id": "g"},
            {"op": "expect", "key": "x", "value": [], "id": "e"},
            {"op": "delete", "key": "x", "id": "d"},
        ])
        self.assertEqual(result["events"][6:], [{"ok": [["x", []]]}, {"ok": []},
                                                 {"ok": True}, {"ok": []}])
        self.assertEqual(result["state"], [["x", ["a", "b"]]])

    def test_pipeline_scalar_values_and_python_expect_equality(self):
        for value in (None, True, 1, "雪", {"nested": [False]}):
            with patch.object(api, "compute", return_value=model.Result(value)) as compute:
                with patch.object(api, "present", wraps=render.present) as present:
                    result = journal([put("x", id="p"), put("x", id="p")])
                    self.assertEqual(result["state"], [["x", value]])
                    self.assertEqual(result["events"], [{"ok": value}, {"ok": value}])
                    compute.assert_called_once_with([])
                    present.assert_called_once()
        with patch.object(core, "solve", return_value={"a": [True, False]}):
            self.assertEqual(journal([put("x"), {"op": "expect", "key": "x",
                                                "value": {"a": [1, 0]}}])["events"][-1],
                             {"ok": True})

    def test_mutable_ownership_boundaries(self):
        state, savepoints = {}, []
        source = {"nested": [[]]}
        with patch.object(api, "compute", return_value=model.Result(source)):
            event = api._execute(put("x"), state, savepoints)
        source["nested"][0].append("source")
        event["ok"]["nested"][0].append("event")
        self.assertEqual(state, {"x": {"nested": [[]]}})
        api._execute({"op": "begin"}, state, savepoints)
        read = api._execute({"op": "get", "key": "x"}, state, savepoints)
        listing = api._execute({"op": "list"}, state, savepoints)
        read["ok"]["nested"].append(1)
        listing["ok"][0][1]["nested"].append(2)
        state["x"]["nested"].append(3)
        self.assertEqual(savepoints, [{"x": {"nested": [[]]}}])
        snapshot = savepoints[0]
        api._execute({"op": "rollback"}, state, savepoints)
        snapshot["x"]["nested"].append(4)
        self.assertEqual(state, {"x": {"nested": [[]]}})

    def test_invocations_are_independent_and_unidentified_commands_repeat(self):
        journal([put("x", id="i"), {"op": "begin"}])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        self.assertEqual(journal([{"op": "list", "id": "i"}]),
                         {"events": [{"ok": []}], "state": [], "depth": 0})
        self.assertEqual(journal([{"op": "begin"}, {"op": "begin"}])["depth"], 2)


if __name__ == "__main__":
    unittest.main()
