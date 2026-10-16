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


def put(key, node, **extra):
    return {"op": "put", "key": key, "input": [[node, node]], **extra}


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([["b", "a"]])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, [["a", "b"]])
        with self.assertRaises(FrozenInstanceError):
            result.value = None

    def test_pipeline_preserves_json_values(self):
        for value in [None, False, True, 0, 1, 1.25, "é", [], [None, {"a": True}], {}]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIs(result.value, value)
                encoded = render.present(result)
                self.assertIsInstance(encoded, str)
                self.assertEqual(json.loads(encoded), value)
                output = journal([{"op": "put", "key": "", "input": []}])
                self.assertEqual(output["events"], [{"ok": value}])
                self.assertEqual(output["state"], [["", value]])

    def test_components_and_input_ownership(self):
        rows = [["z", "z"], ["b", "a"], ["c", "b"], ["b", "a"],
                ["é", ""], ["A", "A"]]
        original = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), [["", "é"], ["A"], ["a", "b", "c"], ["z"]])
        self.assertEqual(rows, original)
        self.assertEqual(core.solve([]), [])

    def test_large_component_is_iterative(self):
        rows = [[str(i), str(i + 1)] for i in range(3000)]
        self.assertEqual(core.solve(rows), [sorted(str(i) for i in range(3001))])

    def test_random_graphs_against_set_merging(self):
        rng = random.Random(17)
        for _ in range(100):
            rows = [[str(rng.randrange(20)), str(rng.randrange(20))]
                    for _ in range(rng.randrange(60))]
            groups = []
            for left, right in rows:
                merged = {left, right}
                remaining = []
                for group in groups:
                    if group & merged:
                        merged |= group
                    else:
                        remaining.append(group)
                groups = remaining + [merged]
            self.assertEqual(core.solve(rows), sorted(sorted(group) for group in groups))


class JournalTests(unittest.TestCase):
    def test_crud_sorting_and_expectations(self):
        commands = [put("é", "b"), put("", "a"), put("A", "c"),
                    {"op": "get", "key": ""}, {"op": "list"},
                    {"op": "expect", "key": "", "value": [["a"]]},
                    {"op": "expect", "key": "absent", "value": None},
                    {"op": "expect", "key": "", "value": []},
                    {"op": "delete", "key": "A"},
                    {"op": "get", "key": "A"}, {"op": "delete", "key": "A"}]
        original = copy.deepcopy(commands)
        output = journal(commands)
        self.assertEqual(output, {
            "events": [{"ok": [["b"]]}, {"ok": [["a"]]}, {"ok": [["c"]]},
                       {"ok": [["a"]]},
                       {"ok": [["", [["a"]]], ["A", [["c"]]], ["é", [["b"]]]]},
                       {"ok": True}, {"error": "expectation"}, {"error": "expectation"},
                       {"ok": [["c"]]}, {"error": "missing"}, {"error": "missing"}],
            "state": [["", [["a"]]], ["é", [["b"]]]], "depth": 0})
        self.assertEqual(commands, original)

    def test_nested_transactions(self):
        output = journal([put("k", "a"), {"op": "begin"}, put("k", "b"),
                          {"op": "begin"}, {"op": "delete", "key": "k"},
                          {"op": "rollback"}, {"op": "get", "key": "k"},
                          {"op": "commit"}, {"op": "rollback"}, {"op": "commit"}])
        self.assertEqual(output["events"][3:8], [{"ok": 2}, {"ok": [["b"]]},
                                                 {"ok": 1}, {"ok": [["b"]]}, {"ok": 0}])
        self.assertEqual(output["events"][-2:], [{"error": "transaction"}] * 2)
        self.assertEqual(output["state"], [["k", [["b"]]]])
        self.assertEqual(output["depth"], 0)
        output = journal([put("k", "a"), {"op": "begin"}, put("k", "b"),
                          {"op": "begin"}, put("k", "c"), {"op": "commit"},
                          {"op": "rollback"}])
        self.assertEqual(output["state"], [["k", [["a"]]]])

    def test_malformed_commands_are_atomic(self):
        malformed = [None, [], "get", 3, True, {}, {"op": []}, {"op": {}},
                     {"op": "unknown"}, {"op": "put", "key": "k"},
                     {"op": "expect", "key": "k"}]
        for op in ["put", "get", "delete", "expect"]:
            for key in [None, 1, False, [], {}]:
                malformed.append({"op": op, "key": key, "input": [], "value": []})
            malformed.append({"op": op, "input": [], "value": []})
        for op in ["put", "get", "delete", "expect", "begin", "commit", "rollback", "list"]:
            for invalid_id in [None, 1, False, [], {}]:
                malformed.append({"op": op, "key": "k", "input": [],
                                  "value": [["a"]], "id": invalid_id})
        output = journal([put("k", "a"), {"op": "begin"}] + malformed)
        self.assertEqual(output["events"][2:], [{"error": "command"}] * len(malformed))
        self.assertEqual(output["state"], [["k", [["a"]]]])
        self.assertEqual(output["depth"], 1)

    def test_extra_fields_ignored_for_execution(self):
        output = journal([{"op": "begin", "key": [], "value": None},
                          {"op": "list", "input": None}, {"op": "commit", "key": 2}])
        self.assertEqual(output["events"], [{"ok": 1}, {"ok": []}, {"ok": 0}])

    def test_id_identity_and_validation_order(self):
        first = put("k", "a", id="", extra={"x": [True], "y": 0})
        equivalent = {"extra": {"y": False, "x": [1]}, "input": [["a", "a"]],
                      "key": "k", "id": "", "op": "put"}
        output = journal([first, {"op": "delete", "key": "k"}, equivalent,
                          {"id": ""}, {"op": [], "id": ""},
                          put("k", "a", id="", extra={"x": [True], "y": 2}),
                          {"op": "begin", "id": None}])
        self.assertEqual(output["events"][:3], [{"ok": [["a"]]}] * 3)
        self.assertEqual(output["events"][3:6], [{"error": "id-conflict"}] * 3)
        self.assertEqual(output["events"][6], {"error": "command"})
        self.assertEqual(output["state"], [])

    def test_failures_do_not_reserve_ids(self):
        failed = [{"op": "get", "key": "k", "id": "x"},
                  {"op": "commit", "id": "x"}, {"op": "put", "id": "x"},
                  {"op": "expect", "key": "k", "value": None, "id": "x"}]
        output = journal(failed + [put("k", "a", id="x")])
        self.assertEqual(output["events"], [{"error": "missing"}, {"error": "transaction"},
                                             {"error": "command"}, {"error": "expectation"},
                                             {"ok": [["a"]]}])

    def test_cache_survives_rollback(self):
        saved_put = put("k", "a", id="p")
        output = journal([{"op": "begin"}, saved_put, {"op": "rollback"}, saved_put])
        self.assertEqual(output["events"][-1], {"ok": [["a"]]})
        self.assertEqual(output["state"], [])

    def test_replays_have_no_control_side_effects(self):
        begin = {"op": "begin", "id": "b"}
        rollback = {"op": "rollback", "id": "r"}
        commit = {"op": "commit", "id": "c"}
        output = journal([begin, begin, rollback, rollback, begin,
                          {"op": "begin"}, commit, {"op": "begin"}, commit])
        self.assertEqual(output["events"], [{"ok": n} for n in [1, 1, 0, 0, 1, 1, 0, 1, 0]])
        self.assertEqual(output["depth"], 1)

    def test_replay_get_delete_list_and_expect(self):
        for op, extra, cached in [("get", {"key": "k"}, [["a"]]),
                                  ("delete", {"key": "k"}, [["a"]]),
                                  ("list", {}, [["k", [["a"]]]]),
                                  ("expect", {"key": "k", "value": [["a"]]}, True)]:
            with self.subTest(op=op):
                command = {"op": op, "id": "x", **extra}
                output = journal([put("k", "a"), command, put("k", "b"), command])
                self.assertEqual(output["events"][-1], {"ok": cached})
                self.assertEqual(output["state"], [["k", [["b"]]]])

    def test_python_equality_for_expect(self):
        with patch.object(core, "solve", return_value={"items": [True, False]}):
            output = journal([put("k", "a"),
                              {"op": "expect", "key": "k", "value": {"items": [1, 0]}}])
        self.assertEqual(output["events"][-1], {"ok": True})

    def test_mutable_values_are_isolated(self):
        state, stack = {}, []
        value = [["a"]]
        with patch.object(core, "solve", return_value=value):
            event = api._execute(put("k", "a"), state, stack)
        value[0].append("external")
        event["ok"][0].append("event")
        api._execute({"op": "begin"}, state, stack)
        state["k"][0].append("live")
        self.assertEqual(stack, [{"k": [["a"]]}])
        snapshot = stack[0]
        api._execute({"op": "rollback"}, state, stack)
        snapshot["k"][0].append("snapshot")
        self.assertEqual(state, {"k": [["a"]]})
        for op in ["get", "list"]:
            event = api._execute({"op": op, "key": "k"}, state, stack)
            event["ok"].clear()
            self.assertEqual(state, {"k": [["a"]]})

    def test_runs_are_independent(self):
        journal([put("k", "a", id="x"), {"op": "begin"}])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        output = journal([put("k", "b", id="x")])
        self.assertEqual(output["events"], [{"ok": [["b"]]}])


if __name__ == "__main__":
    unittest.main()
