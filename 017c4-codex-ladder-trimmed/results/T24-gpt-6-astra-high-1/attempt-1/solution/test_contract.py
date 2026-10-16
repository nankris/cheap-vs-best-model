import copy
from dataclasses import FrozenInstanceError, fields, is_dataclass
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
    return dict(op="put", key=key, input=[["set", "v", value]], **extra)


class PipelineTests(unittest.TestCase):
    def test_result_contract(self):
        self.assertTrue(is_dataclass(model.Result))
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        result = service.compute([])
        self.assertIsInstance(result, model.Result)
        with self.assertRaises(FrozenInstanceError):
            result.value = None

    def test_serialization_and_pipeline_preserve_all_json_shapes(self):
        for value in [None, True, False, 0, 1.5, "雪", [], [1, None], {"a": [True]}]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertEqual(result.value, value)
                self.assertEqual(json.loads(render.present(result)), value)
                with patch.object(api, "compute", wraps=service.compute) as compute:
                    with patch.object(api, "present", wraps=render.present) as present:
                        output = journal([{"op": "put", "key": "", "input": []}])
                compute.assert_called_once_with([])
                present.assert_called_once()
                self.assertEqual(output, {"events": [{"ok": value}],
                                          "state": [["", value]], "depth": 0})

    def test_algorithm_nested_transactions_and_ownership(self):
        rows = [["commit"], ["rollback"], ["set", "雪", {"a": [1]}],
                ["set", "", False], ["begin"], ["set", "雪", 2],
                ["begin"], ["delete", ""], ["set", "x", None],
                ["commit"], ["rollback"], ["delete", "absent"]]
        original = copy.deepcopy(rows)
        result = core.solve(rows)
        self.assertEqual(result, [["", False], ["雪", {"a": [1]}]])
        self.assertEqual(rows, original)
        result[1][1]["a"].append(9)
        self.assertEqual(rows, original)
        rows[2][2]["a"].append(8)
        self.assertEqual(result[1][1]["a"], [1, 9])

    def test_algorithm_commits_and_unclosed_savepoints(self):
        self.assertEqual(core.solve([["set", "a", 1], ["begin"],
                                     ["set", "a", 2], ["commit"],
                                     ["rollback"], ["begin"], ["set", "b", 3]]),
                         [["a", 2], ["b", 3]])


class JournalTests(unittest.TestCase):
    def test_crud_expect_and_unicode_sort(self):
        commands = [put("雪", {"nested": [1, None]}), put("", True), put("a", 3),
                    {"op": "get", "key": ""},
                    {"op": "expect", "key": "", "value": [["v", 1]]},
                    {"op": "expect", "key": "a", "value": 3},
                    {"op": "expect", "key": "absent", "value": None},
                    {"op": "list"}, {"op": "delete", "key": "a"},
                    {"op": "get", "key": "a"}, {"op": "delete", "key": "a"}]
        original = copy.deepcopy(commands)
        result = journal(commands)
        self.assertEqual(commands, original)
        self.assertEqual(result["events"][3:7], [
            {"ok": [["v", True]]}, {"ok": True},
            {"error": "expectation"}, {"error": "expectation"}])
        self.assertEqual([row[0] for row in result["events"][7]["ok"]], ["", "a", "雪"])
        self.assertEqual(result["events"][8:], [
            {"ok": [["v", 3]]}, {"error": "missing"}, {"error": "missing"}])
        self.assertEqual([row[0] for row in result["state"]], ["", "雪"])

    def test_nested_savepoints_and_expect_failure(self):
        result = journal([put("k", 1), {"op": "begin"}, put("k", 2),
                          {"op": "begin"}, {"op": "delete", "key": "k"},
                          {"op": "commit"}, {"op": "expect", "key": "k", "value": []},
                          {"op": "list"}, {"op": "rollback"}, {"op": "get", "key": "k"},
                          {"op": "commit"}, {"op": "rollback"}, {"op": "begin"}])
        self.assertEqual(result["events"][7], {"ok": []})
        self.assertEqual(result["events"][9], {"ok": [["v", 1]]})
        self.assertEqual(result["events"][10:12], [{"error": "transaction"}] * 2)
        self.assertEqual(result["depth"], 1)
        self.assertEqual(result["state"], [["k", [["v", 1]]]])

    def test_malformed_controls_are_atomic(self):
        malformed = [None, [], True, 3, "put", {}, {"op": []}, {"op": {}},
                     {"op": "unknown"}, {"op": "put", "key": "k"},
                     {"op": "put", "input": []}, {"op": "expect", "key": "k"}]
        for op in ["put", "get", "delete", "expect"]:
            for key in [None, 1, False, [], {}]:
                malformed.append({"op": op, "key": key, "input": [], "value": None})
            malformed.append({"op": op})
        for op in ["begin", "rollback", "commit", "list"]:
            for bad_id in [None, 0, False, [], {}]:
                malformed.append({"op": op, "id": bad_id})
        result = journal([put("k", 1), {"op": "begin"}] + malformed + [{"op": "list"}])
        self.assertEqual(result["events"][2:-1], [{"error": "command"}] * len(malformed))
        self.assertEqual(result["state"], [["k", [["v", 1]]]])
        self.assertEqual(result["depth"], 1)

    def test_replay_transactions_has_no_side_effects(self):
        result = journal([{"op": "begin", "id": "b"}, {"op": "begin", "id": "b"},
                          put("k", 1), {"op": "rollback", "id": "r"}, put("k", 2),
                          {"op": "rollback", "id": "r"}, {"op": "begin"},
                          {"op": "commit", "id": "c"}, {"op": "begin"},
                          {"op": "commit", "id": "c"}])
        self.assertEqual(result["events"][0:2], [{"ok": 1}] * 2)
        self.assertEqual(result["events"][5], {"ok": 0})
        self.assertEqual(result["events"][-1], {"ok": 0})
        self.assertEqual(result["depth"], 1)
        self.assertEqual(result["state"], [["k", [["v", 2]]]])

    def test_cache_survives_rollback_and_put_replay_does_not_store(self):
        command = put("k", {"a": [1]}, id="")
        result = journal([{"op": "begin"}, command, {"op": "rollback"}, command,
                          {"op": "get", "key": "k"}])
        self.assertEqual(result["events"][1], result["events"][3])
        self.assertEqual(result["events"][-1], {"error": "missing"})
        self.assertEqual(result["state"], [])

    def test_identity_uses_full_structure_and_python_equality(self):
        command = put("k", True, id="x", extra={"a": 1, "b": [False]})
        equal = {"extra": {"b": [0], "a": True}, "input": [["set", "v", 1]],
                 "key": "k", "op": "put", "id": "x"}
        result = journal([command, equal, dict(equal, extra={}),
                          {"op": "put", "id": "x"}, {"id": "x"}])
        self.assertEqual(result["events"][:2], [{"ok": [["v", True]]}] * 2)
        self.assertEqual(result["events"][2:], [{"error": "id-conflict"}] * 3)

    def test_failures_do_not_reserve_ids(self):
        commands = [{"op": "get", "key": "k", "id": "x"},
                    {"op": "commit", "id": "x"}, {"op": "bogus", "id": "x"},
                    {"op": "expect", "key": "k", "value": None, "id": "x"},
                    put("k", 1, id="x")]
        result = journal(commands)
        self.assertEqual(result["events"][:-1], [{"error": error} for error in
                                                  ["missing", "transaction", "command", "expectation"]])
        self.assertEqual(result["events"][-1], {"ok": [["v", 1]]})

    def test_cached_reads_and_deletes_preserve_original_values(self):
        result = journal([put("k", {"x": [1]}), {"op": "get", "key": "k", "id": "g"},
                          {"op": "list", "id": "l"},
                          {"op": "delete", "key": "k", "id": "d"}, put("k", 2),
                          {"op": "get", "key": "k", "id": "g"},
                          {"op": "list", "id": "l"},
                          {"op": "delete", "key": "k", "id": "d"}])
        self.assertEqual(result["events"][1:4], result["events"][5:8])
        self.assertEqual(result["state"], [["k", [["v", 2]]]])

    def test_extra_fields_ignored_and_commands_without_ids_repeat(self):
        result = journal([{"op": "begin", "key": [], "input": None},
                          {"op": "begin"}, {"op": "begin"},
                          {"op": "list", "value": "ignored"}])
        self.assertEqual(result, {"events": [{"ok": 1}, {"ok": 2}, {"ok": 3}, {"ok": []}],
                                  "state": [], "depth": 3})

    def test_runs_are_isolated(self):
        journal([put("k", 1, id="x"), {"op": "begin"}])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        self.assertEqual(journal([put("k", 2, id="x")])["events"], [{"ok": [["v", 2]]}])


if __name__ == "__main__":
    unittest.main()
