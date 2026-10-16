import copy
import dataclasses
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


def put(key, value, **extra):
    return {"op": "put", "key": key,
            "input": [["set", "value", value]], **extra}


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result_and_arbitrary_json(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([f.name for f in dataclasses.fields(model.Result)],
                         ["value"])
        for value in (None, False, 7, 2.5, "é", [], {"a": [True, None]}):
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIsInstance(result, model.Result)
                self.assertEqual(json.loads(render.present(result)), value)
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    result.value = "changed"

    def test_nested_algorithm_transactions(self):
        rows = [["commit"], ["rollback"], ["delete", "missing"],
                ["set", "z", {"nested": [1]}], ["begin"],
                ["set", "z", 2], ["begin"], ["set", "a", 3],
                ["commit"], ["rollback"], ["set", "", None],
                ["set", "é", False], ["begin"], ["delete", "z"],
                ["rollback"]]
        before = copy.deepcopy(rows)
        result = core.solve(rows)
        self.assertEqual(result, [["", None], ["z", {"nested": [1]}], ["é", False]])
        self.assertEqual(rows, before)
        result[1][1]["nested"].append(2)
        self.assertEqual(rows, before)
        rows[3][2]["nested"].append(3)
        self.assertEqual(result[1][1]["nested"], [1, 2])

    def test_unclosed_algorithm_transaction_retains_current_state(self):
        self.assertEqual(core.solve([["begin"], ["set", "b", 1],
                                     ["begin"], ["set", "a", 2], ["commit"]]),
                         [["a", 2], ["b", 1]])

    def test_api_uses_pipeline_and_preserves_shapes(self):
        for value in (None, True, 4, "text", [], {"x": [1]}):
            with self.subTest(value=value), patch.object(core, "solve", return_value=value), \
                    patch.object(api, "present", wraps=render.present) as present:
                output = journal([put("k", 0), {"op": "get", "key": "k"}])
                self.assertEqual(output, {"events": [{"ok": value}, {"ok": value}],
                                          "state": [["k", value]], "depth": 0})
                self.assertIsInstance(present.call_args.args[0], model.Result)


class JournalTests(unittest.TestCase):
    def test_empty_and_fresh_invocations(self):
        journal([put("x", 1, id="p"), {"op": "begin", "id": "b"}])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        result = journal([put("x", 2, id="p"), {"op": "begin", "id": "b"}])
        self.assertEqual(result["events"], [{"ok": [["value", 2]]}, {"ok": 1}])

    def test_crud_order_empty_keys_and_expect(self):
        commands = [put("é", True), put("", None), put("Z", [1]),
                    {"op": "list"},
                    {"op": "expect", "key": "é", "value": [["value", 1]]},
                    {"op": "expect", "key": "absent", "value": None},
                    {"op": "delete", "key": "Z"}, {"op": "get", "key": "Z"},
                    {"op": "delete", "key": "Z"}]
        output = journal(commands)
        self.assertEqual(output["events"][3], {"ok": [["", [["value", None]]],
                                                      ["Z", [["value", [1]]]],
                                                      ["é", [["value", True]]]]})
        self.assertEqual(output["events"][4:], [
            {"ok": True}, {"error": "expectation"}, {"ok": [["value", [1]]]},
            {"error": "missing"}, {"error": "missing"}])
        self.assertEqual([row[0] for row in output["state"]], ["", "é"])

    def test_nested_journal_transactions_and_event_isolation(self):
        output = journal([put("a", {"x": [1]}), {"op": "begin"}, put("a", 2),
                          {"op": "begin"}, {"op": "delete", "key": "a"},
                          {"op": "commit"}, {"op": "list"}, {"op": "rollback"},
                          {"op": "get", "key": "a"}, {"op": "rollback"},
                          {"op": "commit"}])
        original = [["value", {"x": [1]}]]
        self.assertEqual(output["events"], [
            {"ok": original}, {"ok": 1}, {"ok": [["value", 2]]}, {"ok": 2},
            {"ok": [["value", 2]]}, {"ok": 1}, {"ok": []}, {"ok": 0},
            {"ok": original}, {"error": "transaction"}, {"error": "transaction"}])
        self.assertEqual(output["state"], [["a", original]])

    def test_malformed_controls_are_atomic(self):
        malformed = [None, [], 1, True, "put", {}, {"op": []}, {"op": {}},
                     {"op": None}, {"op": "unknown"}, {"op": "put", "key": "x"},
                     {"op": "put", "input": []}, {"op": "get"},
                     {"op": "delete", "key": 1}, {"op": "expect", "key": "x"},
                     {"op": "expect", "key": None, "value": None}]
        for op in ("put", "get", "delete", "expect"):
            for key in (None, False, 4, [], {}):
                malformed.append({"op": op, "key": key, "input": [], "value": None})
        for identifier in (None, False, 0, [], {}):
            malformed.append({"op": "rollback", "id": identifier})
        commands = [put("x", 1), {"op": "begin"}] + malformed + [{"op": "list"}]
        output = journal(commands)
        self.assertEqual(output["events"][2:-1], [{"error": "command"}] * len(malformed))
        self.assertEqual(output["depth"], 1)
        self.assertEqual(output["state"], [["x", [["value", 1]]]])

    def test_extra_fields_ignored_for_execution(self):
        output = journal([{"op": "begin", "key": [], "value": {}, "input": None},
                          {"op": "list", "key": False}, {"op": "rollback"}])
        self.assertEqual(output["events"], [{"ok": 1}, {"ok": []}, {"ok": 0}])

    def test_replay_put_does_not_restore_deleted_state(self):
        command = put("x", {"a": [1]}, id="")
        output = journal([command, {"op": "delete", "key": "x"}, command])
        self.assertEqual(output["events"], [{"ok": [["value", {"a": [1]}]]}] * 3)
        self.assertEqual(output["state"], [])

    def test_identity_python_equality_extra_fields_and_validation_order(self):
        first = {"op": "list", "id": "i", "extra": {"a": [True], "b": None}}
        same = {"extra": {"b": None, "a": [1]}, "id": "i", "op": "list"}
        output = journal([first, same, {"op": "list", "id": "i"},
                          {"op": "put", "id": "i"},
                          {"op": [], "id": "i"}, {"op": "list", "id": None}])
        self.assertEqual(output["events"], [{"ok": []}, {"ok": []},
                                          {"error": "id-conflict"},
                                          {"error": "id-conflict"},
                                          {"error": "id-conflict"},
                                          {"error": "command"}])

    def test_failures_do_not_reserve_ids(self):
        failures = [{"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
                    {"op": "expect", "key": "x", "value": None},
                    {"op": "commit"}, {"op": "rollback"}, {"op": "put"}]
        for failure in failures:
            with self.subTest(failure=failure):
                output = journal([{**failure, "id": "i"}, {"op": "list", "id": "i"}])
                self.assertIn("error", output["events"][0])
                self.assertEqual(output["events"][1], {"ok": []})

    def test_transaction_replay_and_cache_survives_rollback(self):
        begin = {"op": "begin", "id": "b"}
        rollback = {"op": "rollback", "id": "r"}
        write = put("x", 1, id="p")
        output = journal([begin, begin, write, rollback, write,
                          {"op": "begin"}, rollback, begin])
        self.assertEqual(output["events"], [{"ok": 1}, {"ok": 1},
                                          {"ok": [["value", 1]]}, {"ok": 0},
                                          {"ok": [["value", 1]]}, {"ok": 1},
                                          {"ok": 0}, {"ok": 1}])
        self.assertEqual(output["state"], [])
        self.assertEqual(output["depth"], 1)

    def test_cached_reads_list_delete_expect_and_commit(self):
        read = {"op": "get", "key": "x", "id": "g"}
        listing = {"op": "list", "id": "l"}
        expect = {"op": "expect", "key": "x", "value": [["value", 1]], "id": "e"}
        delete = {"op": "delete", "key": "x", "id": "d"}
        commit = {"op": "commit", "id": "c"}
        output = journal([put("x", 1), read, listing, expect, delete, put("x", 2),
                          read, listing, expect, delete, {"op": "begin"}, commit,
                          {"op": "begin"}, commit])
        events = output["events"]
        for old, replay in ((1, 6), (2, 7), (3, 8), (4, 9), (11, 13)):
            self.assertEqual(events[old], events[replay])
        self.assertEqual(output["state"], [["x", [["value", 2]]]])
        self.assertEqual(output["depth"], 1)

    def test_expect_failure_does_not_rollback(self):
        output = journal([{"op": "begin"}, put("x", 1),
                          {"op": "expect", "key": "x", "value": None}])
        self.assertEqual(output["events"][-1], {"error": "expectation"})
        self.assertEqual(output["state"], [["x", [["value", 1]]]])
        self.assertEqual(output["depth"], 1)


if __name__ == "__main__":
    unittest.main()
