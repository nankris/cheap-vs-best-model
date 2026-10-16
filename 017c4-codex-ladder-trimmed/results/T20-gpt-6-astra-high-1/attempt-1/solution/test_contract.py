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


class AlgorithmTests(unittest.TestCase):
    def test_examples_and_input_ownership(self):
        rows = [[3, 5, 8], [0, 3, 4], [0, 5, 11], [3, 5, 8], [5, 6, -2]]
        original = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), 12)
        self.assertEqual(rows, original)
        self.assertEqual(core.solve([]), 0)
        self.assertEqual(core.solve([[0, 1, -3]]), 0)

    def test_against_exhaustive_search(self):
        rng = random.Random(17)
        for _ in range(200):
            rows = []
            for _ in range(rng.randrange(9)):
                start = rng.randrange(-3, 7)
                rows.append([start, start + rng.randrange(1, 5), rng.randrange(-8, 15)])
            expected = 0
            for mask in range(1 << len(rows)):
                chosen = sorted(row for i, row in enumerate(rows) if mask & (1 << i))
                if all(a[1] <= b[0] for a, b in zip(chosen, chosen[1:])):
                    expected = max(expected, sum(row[2] for row in chosen))
            self.assertEqual(core.solve(rows), expected)

    def test_large_input(self):
        self.assertEqual(core.solve([[i, i + 1, 1] for i in range(20000, 0, -1)]), 20000)


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([[0, 1, 7]])
        self.assertIs(type(result), model.Result)
        self.assertEqual(result.value, 7)
        with self.assertRaises(FrozenInstanceError):
            result.value = 8

    def test_json_values_are_preserved(self):
        for value in [None, False, 0, 2.5, "é", [1, None, {"x": True}], {"a": []}]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertEqual(result.value, value)
                self.assertEqual(json.loads(render.present(result)), value)
                self.assertEqual(journal([{"op": "put", "key": "", "input": []}]), {
                    "events": [{"ok": value}], "state": [["", value]], "depth": 0,
                })


class JournalTests(unittest.TestCase):
    def test_state_sorting_expect_delete_and_reset(self):
        commands = [
            {"op": "put", "key": key, "input": [[0, 1, 1]]}
            for key in ["😀", "é", "a", ""]
        ]
        commands += [
            {"op": "expect", "key": "", "value": True},
            {"op": "expect", "key": "absent", "value": None},
            {"op": "list"}, {"op": "delete", "key": "a"},
            {"op": "get", "key": "a"}, {"op": "delete", "key": "a"},
        ]
        original = copy.deepcopy(commands)
        result = journal(commands)
        self.assertEqual(commands, original)
        self.assertEqual(result["events"][4:], [
            {"ok": True}, {"error": "expectation"},
            {"ok": [["", 1], ["a", 1], ["é", 1], ["😀", 1]]},
            {"ok": 1}, {"error": "missing"}, {"error": "missing"},
        ])
        self.assertEqual(result["state"], [["", 1], ["é", 1], ["😀", 1]])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})

    def test_nested_transactions(self):
        result = journal([
            {"op": "commit"}, {"op": "rollback"}, {"op": "begin"},
            {"op": "put", "key": "x", "input": [[0, 1, 2]]},
            {"op": "begin"}, {"op": "delete", "key": "x"},
            {"op": "commit"}, {"op": "rollback"}, {"op": "begin"},
        ])
        self.assertEqual(result, {
            "events": [{"error": "transaction"}, {"error": "transaction"},
                       {"ok": 1}, {"ok": 2}, {"ok": 2}, {"ok": 2},
                       {"ok": 1}, {"ok": 0}, {"ok": 1}],
            "state": [], "depth": 1,
        })

    def test_invalid_commands_are_atomic(self):
        invalid = [None, [], 5, "put", {}, {"op": []}, {"op": {}},
                   {"op": "unknown"}, {"op": "put", "key": "x"},
                   {"op": "put", "input": []}, {"op": "get"},
                   {"op": "delete", "key": False},
                   {"op": "expect", "key": "x"},
                   {"op": "expect", "key": 2, "value": 0}]
        invalid += [{"op": "begin", "id": value} for value in [None, False, 1, [], {}]]
        result = journal([{"op": "begin"}] + invalid)
        self.assertEqual(result["events"], [{"ok": 1}] + [{"error": "command"}] * len(invalid))
        self.assertEqual(result["state"], [])
        self.assertEqual(result["depth"], 1)
        self.assertEqual(journal([{"op": "list", "key": None, "extra": 2}])["events"], [{"ok": []}])

    def test_identity_equality_conflicts_and_validation_order(self):
        first = {"op": "put", "key": "", "input": [], "id": "", "extra": {"a": [True], "b": 2}}
        equal = {"extra": {"b": 2.0, "a": [1]}, "id": "", "input": [], "key": "", "op": "put"}
        result = journal([
            first, {"op": "delete", "key": ""}, equal,
            {"op": "put", "key": "", "input": [], "id": ""},
            {"id": ""}, {"op": [], "id": ""},
            {"op": "begin", "id": None},
        ])
        self.assertEqual(result["events"], [
            {"ok": 0}, {"ok": 0}, {"ok": 0},
            {"error": "id-conflict"}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "command"},
        ])
        self.assertEqual(result["state"], [])

    def test_failures_do_not_reserve_ids(self):
        result = journal([
            {"op": "get", "key": "x", "id": "id"},
            {"op": "commit", "id": "id"},
            {"op": "expect", "key": "x", "value": 1, "id": "id"},
            {"op": "put", "id": "id"},
            {"op": "begin", "id": "id"},
        ])
        self.assertEqual(result["events"], [
            {"error": "missing"}, {"error": "transaction"}, {"error": "expectation"},
            {"error": "command"}, {"ok": 1},
        ])
        self.assertEqual(journal([{"op": "list", "id": "id"}])["events"], [{"ok": []}])

    def test_transaction_and_list_replays_have_no_effects(self):
        result = journal([
            {"op": "begin", "id": "b"}, {"op": "begin", "id": "b"},
            {"op": "put", "key": "x", "input": [[0, 1, 3]], "id": "p"},
            {"op": "list", "id": "l"}, {"op": "rollback", "id": "r"},
            {"op": "put", "key": "x", "input": [[0, 1, 3]], "id": "p"},
            {"op": "list", "id": "l"}, {"op": "begin"},
            {"op": "rollback", "id": "r"}, {"op": "commit", "id": "c"},
            {"op": "begin"}, {"op": "commit", "id": "c"},
        ])
        self.assertEqual(result["events"], [
            {"ok": 1}, {"ok": 1}, {"ok": 3}, {"ok": [["x", 3]]},
            {"ok": 0}, {"ok": 3}, {"ok": [["x", 3]]}, {"ok": 1},
            {"ok": 0}, {"ok": 0}, {"ok": 1}, {"ok": 0},
        ])
        self.assertEqual(result["state"], [])
        self.assertEqual(result["depth"], 1)

    def test_mutable_values_and_snapshots(self):
        value = {"nested": [1, {"a": []}]}
        original = copy.deepcopy(value)

        def solve(rows):
            if rows:
                value["nested"][1]["a"].append(9)
            return value

        with patch.object(core, "solve", side_effect=solve):
            result = journal([
                {"op": "put", "key": "x", "input": [], "id": "p"},
                {"op": "get", "key": "x", "id": "g"},
                {"op": "begin"},
                {"op": "put", "key": "x", "input": [[0, 1, 1]]},
                {"op": "rollback"}, {"op": "get", "key": "x", "id": "g"},
                {"op": "delete", "key": "x", "id": "d"},
                {"op": "put", "key": "x", "input": [[0, 1, 1]]},
                {"op": "delete", "key": "x", "id": "d"},
            ])
        for index in [0, 1, 5, 6, 8]:
            self.assertEqual(result["events"][index], {"ok": original})
        self.assertEqual(result["events"][3], {"ok": {"nested": [1, {"a": [9]}]}})
        self.assertEqual(result["state"], [["x", value]])


if __name__ == "__main__":
    unittest.main()
