import copy
from dataclasses import FrozenInstanceError, fields
import json
import unittest
from unittest.mock import patch

import api
import core
import model
import render
import service


def value(document):
    return {"ok": True, "document": document}


def put(key, document, **extra):
    return {"op": "put", "key": key, "input": [document, []], **extra}


def run(*commands):
    return json.loads(api.run(json.dumps(commands)))


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_model(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([None, []])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, value(None))
        with self.assertRaises(FrozenInstanceError):
            result.value = 1

    def test_arbitrary_values_survive_pipeline(self):
        for expected in (None, False, 0, 2.5, "é", [None, {"x": True}]):
            with self.subTest(expected=expected), patch.object(core, "solve", return_value=expected):
                result = service.compute([])
                self.assertEqual(result.value, expected)
                serialized = render.present(result)
                self.assertIsInstance(serialized, str)
                self.assertEqual(json.loads(serialized), expected)
                self.assertEqual(run(put("x", None))["state"], [["x", expected]])


class PatchTests(unittest.TestCase):
    def test_all_operations_and_escapes(self):
        rows = [{"a/b": {"~": [1, 3]}, "": 0}, [
            ["add", "/a~1b/~0/1", 2],
            ["add", "/a~1b/~0/-", 4],
            ["replace", "/", 9],
            ["test", "/a~1b/~0", [1, 2, 3, 4]],
            ["remove", "/a~1b/~0/0"],
            ["add", "/new", {"nested": []}],
        ]]
        before = copy.deepcopy(rows)
        result = core.solve(rows)
        self.assertEqual(result, value({"a/b": {"~": [2, 3, 4]}, "": 9, "new": {"nested": []}}))
        self.assertEqual(rows, before)
        result["document"]["new"]["nested"].append(1)
        self.assertEqual(rows, before)

    def test_root_operations(self):
        self.assertEqual(core.solve([1, [["add", "", [1]], ["replace", "", None]]]), value(None))
        self.assertEqual(core.solve([{}, [["remove", ""]]]), value(None))
        self.assertEqual(core.solve([None, [["remove", ""], ["add", "", {}]]]), value({}))
        self.assertEqual(core.solve([True, [["test", "", 1]]]), value(True))

    def test_pointer_decodes_once_and_dict_keys_are_unrestricted(self):
        document = {"~1": 1, "-": 2, "01": 3, "-1": 4}
        operations = [["test", "/~01", 1], ["test", "/-", 2], ["test", "/01", 3], ["test", "/-1", 4]]
        self.assertEqual(core.solve([document, operations]), value(document))

    def test_invalid_patches_are_atomic(self):
        invalid = [
            ["move", "/a", 1], [], {}, ["remove"], ["add", "/a"],
            ["remove", "/a", 1], ["replace", "/missing", 1],
            ["remove", "/missing"], ["test", "/missing", None],
            ["test", "/a", []], ["add", "/missing/child", 1],
            ["add", "a", 1], ["add", None, 1],
            ["add", "/bad~", 1], ["add", "/bad~2", 1],
            ["add", "/scalar/child", 1], ["remove", "/scalar/child"],
        ]
        for index in ("-1", "01", "+1", "1.0", "", "١", "9" * 5000):
            invalid.append(["add", "/a/" + index, 2])
        invalid.extend([
            ["add", "/a/3", 2], ["replace", "/a/2", 2],
            ["remove", "/a/-"], ["test", "/a/-", 1],
            ["add", "/a/-/child", 2],
        ])
        for operation in invalid:
            with self.subTest(operation=repr(operation)[:100]):
                rows = [{"a": [1, 2], "scalar": 5}, [["add", "/changed", 1], operation]]
                before = copy.deepcopy(rows)
                result = core.solve(rows)
                self.assertEqual(result, {"ok": False, "document": before[0]})
                self.assertEqual(rows, before)
                result["document"]["a"].append(9)
                self.assertEqual(rows, before)

    def test_list_boundaries_and_dict_overwrite(self):
        self.assertEqual(core.solve([[], [["add", "/0", 1], ["add", "/1", 2], ["remove", "/0"]]]), value([2]))
        self.assertEqual(core.solve([{"a": 1}, [["add", "/a", 2]]]), value({"a": 2}))
        self.assertEqual(core.solve([[], [["replace", "/0", 1]]]), {"ok": False, "document": []})


class JournalTests(unittest.TestCase):
    def test_basic_commands_sorted_state_and_event_isolation(self):
        result = run(put("é", [1]), put("", None), put("a", False),
                     {"op": "list"}, put("é", [2]), {"op": "get", "key": "é"},
                     {"op": "delete", "key": "a"}, {"op": "get", "key": "a"},
                     {"op": "delete", "key": "a"})
        self.assertEqual(result["events"][3], {"ok": [["", value(None)], ["a", value(False)], ["é", value([1])]]})
        self.assertEqual(result["events"][0], {"ok": value([1])})
        self.assertEqual(result["events"][5:7], [{"ok": value([2])}, {"ok": value(False)}])
        self.assertEqual(result["events"][-2:], [{"error": "missing"}] * 2)
        self.assertEqual(result["state"], [["", value(None)], ["é", value([2])]])
        self.assertEqual(result["depth"], 0)

    def test_nested_transactions(self):
        result = run(put("x", 0), {"op": "begin"}, put("x", 1), {"op": "begin"},
                     put("x", 2), {"op": "commit"}, {"op": "rollback"},
                     {"op": "rollback"}, {"op": "commit"}, {"op": "begin"})
        self.assertEqual(result["state"], [["x", value(0)]])
        self.assertEqual(result["depth"], 1)
        self.assertEqual([result["events"][i] for i in (1, 3, 5, 6, 7, 8, 9)],
                         [{"ok": 1}, {"ok": 2}, {"ok": 1}, {"ok": 0},
                          {"error": "transaction"}, {"error": "transaction"}, {"ok": 1}])

    def test_expect_python_equality_and_no_rollback(self):
        result = run({"op": "begin"}, put("x", True),
                     {"op": "expect", "key": "x", "value": {"ok": 1, "document": 1}},
                     {"op": "expect", "key": "x", "value": False},
                     {"op": "expect", "key": "missing", "value": None})
        self.assertEqual(result["events"][2:], [{"ok": True}, {"error": "expectation"}, {"error": "expectation"}])
        self.assertEqual(result["depth"], 1)
        self.assertEqual(result["state"], [["x", value(True)]])

    def test_malformed_commands_do_not_reserve_ids_or_change_depth(self):
        malformed = [None, [], 1, "get", {}, {"op": []}, {"op": "unknown"},
                     {"op": "put", "key": "x"}, {"op": "put", "input": [1, []]},
                     {"op": "get"}, {"op": "delete", "key": None},
                     {"op": "expect", "key": "x"}, {"op": "get", "key": 1}]
        for command in malformed:
            with self.subTest(command=command):
                if isinstance(command, dict):
                    command = dict(command, id="same")
                result = run({"op": "begin"}, command, {"op": "list", "id": "same"})
                self.assertEqual(result, {"events": [{"ok": 1}, {"error": "command"}, {"ok": []}], "state": [], "depth": 1})
        for bad_id in (None, False, 1, [], {}):
            self.assertEqual(run({"op": "begin", "id": bad_id})["events"], [{"error": "command"}])

    def test_replay_has_no_side_effects_and_cache_survives_rollback(self):
        begin = {"op": "begin", "id": "begin"}
        write = put("x", [1], id="put")
        rollback = {"op": "rollback", "id": "rollback"}
        result = run(begin, begin, write, rollback, write, begin,
                     {"op": "begin"}, rollback, {"op": "get", "key": "x"})
        self.assertEqual(result["events"], [{"ok": 1}, {"ok": 1}, {"ok": value([1])},
                         {"ok": 0}, {"ok": value([1])}, {"ok": 1}, {"ok": 1},
                         {"ok": 0}, {"error": "missing"}])
        self.assertEqual(result["state"], [])
        self.assertEqual(result["depth"], 1)

    def test_cached_list_get_delete_and_commit(self):
        listing = {"op": "list", "id": "list"}
        get = {"op": "get", "key": "x", "id": "get"}
        delete = {"op": "delete", "key": "x", "id": "delete"}
        commit = {"op": "commit", "id": "commit"}
        result = run(put("x", [1]), listing, get, delete, put("x", [2]),
                     listing, get, delete, {"op": "begin"}, commit, {"op": "begin"}, commit)
        self.assertEqual(result["events"][1], result["events"][5])
        self.assertEqual(result["events"][2], result["events"][6])
        self.assertEqual(result["events"][3], result["events"][7])
        self.assertEqual(result["state"], [["x", value([2])]])
        self.assertEqual(result["depth"], 1)

    def test_full_identity_python_equality_and_validation_order(self):
        first = {"op": "begin", "extra": {"a": 1, "b": [False]}, "id": ""}
        same = {"id": "", "extra": {"b": [0], "a": True}, "op": "begin"}
        result = run(first, same, {"op": "get", "id": ""},
                     {"op": "begin", "id": ""}, {"op": "begin", "id": None})
        self.assertEqual(result["events"], [{"ok": 1}, {"ok": 1},
                         {"error": "id-conflict"}, {"error": "id-conflict"}, {"error": "command"}])
        self.assertEqual(result["depth"], 1)

    def test_failures_do_not_reserve_ids(self):
        failures = [{"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
                    {"op": "expect", "key": "x", "value": None},
                    {"op": "commit"}, {"op": "rollback"}]
        for command in failures:
            with self.subTest(command=command):
                result = run(dict(command, id="id"), {"op": "begin", "id": "id"})
                self.assertIn("error", result["events"][0])
                self.assertEqual(result["events"][1], {"ok": 1})

    def test_failed_patch_is_successful_put_and_runs_reset(self):
        command = {"op": "put", "key": "x", "input": [0, [["test", "", 1]]], "id": "id"}
        result = run(command, {"op": "list", "id": "id"})
        self.assertEqual(result["events"], [{"ok": {"ok": False, "document": 0}}, {"error": "id-conflict"}])
        self.assertEqual(run({"op": "list", "id": "id"}), {"events": [{"ok": []}], "state": [], "depth": 0})

    def test_unused_fields_are_ignored(self):
        self.assertEqual(run({"op": "begin", "key": None, "value": 1})["events"], [{"ok": 1}])


if __name__ == "__main__":
    unittest.main()
