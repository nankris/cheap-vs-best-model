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


def put(key, rows, **extra):
    return dict(op="put", key=key, input=rows, **extra)


class ContractTests(unittest.TestCase):
    def test_modules_and_serialization(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        for value in (None, False, 0, 1.25, "é", [], [["a"]], {"x": [True]}):
            with patch.object(core, "solve", return_value=value) as solve:
                result = service.compute([])
                solve.assert_called_once_with([])
                self.assertIsInstance(result, model.Result)
                self.assertEqual(json.loads(render.present(result)), value)
                with self.assertRaises(FrozenInstanceError):
                    result.value = "changed"
            with patch.object(core, "solve", return_value=value):
                output = journal([put("", []), {"op": "get", "key": ""}])
                self.assertEqual(output["events"], [{"ok": value}, {"ok": value}])
                self.assertEqual(output["state"], [["", value]])

    def test_components(self):
        rows = [["z", "a"], ["b", "b"], ["a", "z"], ["é", ""]]
        original = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), [["", "é"], ["a", "z"], ["b"]])
        self.assertEqual(rows, original)
        self.assertEqual(core.solve([]), [])
        self.assertEqual(len(core.solve([[str(i), str(i + 1)] for i in range(3000)])[0]), 3001)

    def test_random_components_against_set_merging(self):
        rng = random.Random(42)
        for _ in range(100):
            rows = [[rng.choice("abcde"), rng.choice("abcde")] for _ in range(rng.randrange(20))]
            groups = []
            for left, right in rows:
                merged = {left, right}
                retained = []
                for group in groups:
                    if group & merged:
                        merged |= group
                    else:
                        retained.append(group)
                groups = retained + [merged]
            self.assertEqual(core.solve(rows), sorted(sorted(group) for group in groups))

    def test_nested_transactions_and_event_snapshots(self):
        commands = [put("z", [["a", "a"]]), {"op": "begin"},
                    {"op": "list"}, put("z", [["b", "b"]]),
                    {"op": "begin"}, {"op": "delete", "key": "z"},
                    {"op": "commit"}, {"op": "get", "key": "z"},
                    {"op": "rollback"}, {"op": "get", "key": "z"},
                    {"op": "commit"}, {"op": "rollback"}]
        output = journal(commands)
        self.assertEqual(output, {"events": [
            {"ok": [["a"]]}, {"ok": 1}, {"ok": [["z", [["a"]]]]},
            {"ok": [["b"]]}, {"ok": 2}, {"ok": [["b"]]}, {"ok": 1},
            {"error": "missing"}, {"ok": 0}, {"ok": [["a"]]},
            {"error": "transaction"}, {"error": "transaction"}],
            "state": [["z", [["a"]]]], "depth": 0})

    def test_replay_outside_savepoints_and_validation_precedence(self):
        commands = [{"op": "begin", "id": "b"}, put("x", [], id="p"),
                    {"op": "rollback", "id": "r"}, put("x", [], id="p"),
                    {"op": "begin", "id": "b"}, {"op": "rollback", "id": "r"},
                    {"op": "put", "id": "p"}, {"op": ["bad"], "id": "b"}]
        self.assertEqual(journal(commands), {"events": [
            {"ok": 1}, {"ok": []}, {"ok": 0}, {"ok": []}, {"ok": 1},
            {"ok": 0}, {"error": "id-conflict"}, {"error": "id-conflict"}],
            "state": [], "depth": 0})

    def test_identity_and_failed_ids(self):
        commands = [{"op": "get", "key": "x", "id": ""},
                    put("x", [], id=""),
                    {"op": "list", "id": "l", "extra": {"a": True, "b": [0]}},
                    put("y", []),
                    {"extra": {"b": [False], "a": 1}, "id": "l", "op": "list"},
                    {"op": "list", "id": "l"}]
        output = journal(commands)
        self.assertEqual(output["events"], [
            {"error": "missing"}, {"ok": []}, {"ok": [["x", []]]},
            {"ok": []}, {"ok": [["x", []]]}, {"error": "id-conflict"}])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        self.assertEqual(journal([put("y", [], id="")])["events"], [{"ok": []}])

    def test_malformed_commands_are_atomic(self):
        malformed = [None, [], 1, "put", {}, {"op": []}, {"op": "unknown"},
                     {"op": "put", "key": "x"}, {"op": "get"},
                     {"op": "delete", "key": False}, {"op": "expect", "key": "x"},
                     {"op": "put", "key": None, "input": []}]
        malformed += [{"op": "begin", "id": value} for value in (None, 1, False, [], {})]
        commands = [put("x", []), {"op": "begin"}] + malformed + [{"op": "rollback"}]
        output = journal(commands)
        self.assertEqual(output["events"][2:-1], [{"error": "command"}] * len(malformed))
        self.assertEqual(output["state"], [["x", []]])
        self.assertEqual(output["depth"], 0)
        self.assertEqual(journal([{"op": "get", "id": "retry"},
                                  {"op": "begin", "id": "retry"}])["events"],
                         [{"error": "command"}, {"ok": 1}])

    def test_expect_and_unicode_order(self):
        commands = [put(key, []) for key in ("é", "", "z", "A")]
        commands += [{"op": "expect", "key": "", "value": []},
                     {"op": "expect", "key": "absent", "value": None},
                     {"op": "expect", "key": "", "value": False}, {"op": "list"}]
        output = journal(commands)
        self.assertEqual(output["events"][4:7], [{"ok": True}, {"error": "expectation"},
                                                 {"error": "expectation"}])
        self.assertEqual(output["state"], [[key, []] for key in ("", "A", "z", "é")])
        with patch.object(core, "solve", return_value=[True, False]):
            self.assertEqual(journal([put("x", []), {"op": "expect", "key": "x", "value": [1, 0]}])["events"][-1], {"ok": True})


if __name__ == "__main__":
    unittest.main()
