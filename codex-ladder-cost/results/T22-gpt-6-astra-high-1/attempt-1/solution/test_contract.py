import dataclasses
import json
import random
import unittest
from copy import deepcopy
from unittest.mock import patch

import api
import core
import model
import render
import service


def journal(commands):
    return json.loads(api.run(json.dumps(commands)))


class ContractTests(unittest.TestCase):
    def test_algorithm(self):
        rng = random.Random(42)
        for _ in range(500):
            rows = [[rng.randrange(-10, 11), rng.randrange(-10, 11)]
                    for _ in range(rng.randrange(20))]
            original = deepcopy(rows)
            expected = sum(sum(a <= x < b for a, b in rows) % 2
                           for x in range(-10, 10))
            self.assertEqual(core.solve(rows), expected)
            self.assertEqual(rows, original)
        self.assertEqual(core.solve([[-10**30, 10**30]]), 2 * 10**30)

    def test_pipeline(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([f.name for f in dataclasses.fields(model.Result)], ["value"])
        result = service.compute([[0, 5], [2, 7]])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, 4)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.value = 9
        for value in [None, False, 0, 3.5, "é", [1, {"x": [True]}]]:
            with patch.object(core, "solve", return_value=value):
                computed = service.compute([])
                self.assertEqual(computed.value, value)
                self.assertEqual(json.loads(render.present(computed)), value)
                output = journal([{"op": "put", "key": "", "input": []}])
                self.assertEqual(output["events"], [{"ok": value}])
                self.assertEqual(output["state"], [["", value]])

    def test_transactions_and_order(self):
        commands = [
            {"op": "put", "key": "é", "input": [[0, 4]]},
            {"op": "begin"},
            {"op": "put", "key": "", "input": [[0, 1]]},
            {"op": "begin"},
            {"op": "delete", "key": "é"},
            {"op": "commit"},
            {"op": "expect", "key": "", "value": True},
            {"op": "expect", "key": "é", "value": 4},
            {"op": "list"},
            {"op": "rollback"},
            {"op": "get", "key": ""},
            {"op": "list"},
            {"op": "rollback"},
            {"op": "commit"},
        ]
        self.assertEqual(journal(commands), {
            "events": [{"ok": 4}, {"ok": 1}, {"ok": 1}, {"ok": 2},
                       {"ok": 4}, {"ok": 1}, {"ok": True},
                       {"error": "expectation"}, {"ok": [["", 1]]},
                       {"ok": 0}, {"error": "missing"}, {"ok": [["é", 4]]},
                       {"error": "transaction"}, {"error": "transaction"}],
            "state": [["é", 4]], "depth": 0})

    def test_cache_outside_savepoints_and_replay(self):
        begin = {"op": "begin", "id": "b"}
        put = {"op": "put", "key": "x", "input": [[0, 5]], "id": "p"}
        rollback = {"op": "rollback", "id": "r"}
        listing = {"op": "list", "id": "l"}
        output = journal([begin, begin, put, listing, rollback, put, listing,
                          rollback, begin, {"op": "list"}])
        self.assertEqual(output["events"], [
            {"ok": 1}, {"ok": 1}, {"ok": 5}, {"ok": [["x", 5]]},
            {"ok": 0}, {"ok": 5}, {"ok": [["x", 5]]}, {"ok": 0},
            {"ok": 1}, {"ok": []}])
        self.assertEqual(output["state"], [])
        self.assertEqual(output["depth"], 0)

    def test_validation_identity_and_failed_ids(self):
        invalid = [None, [], 1, "put", {}, {"op": []}, {"op": "unknown"},
                   {"op": "put", "key": "x"}, {"op": "get"},
                   {"op": "delete", "key": None},
                   {"op": "expect", "key": "x"},
                   {"op": "begin", "id": None}, {"op": "list", "id": 1}]
        commands = invalid + [
            {"op": "get", "key": "x", "id": ""},
            {"op": "put", "key": "x", "input": [[0, 1]], "id": "",
             "extra": {"a": 1, "b": [False]}},
            {"extra": {"b": [0], "a": True}, "id": "", "input": [[0, 1]],
             "key": "x", "op": "put"},
            {"op": "put", "id": ""},
            {"op": "get", "key": "x", "id": "", "extra": 2},
            {"op": "list", "key": None},
        ]
        output = journal(commands)
        self.assertEqual(output["events"], [{"error": "command"}] * len(invalid) + [
            {"error": "missing"}, {"ok": 1}, {"ok": 1},
            {"error": "id-conflict"}, {"error": "id-conflict"},
            {"ok": [["x", 1]]}])
        self.assertEqual(output["state"], [["x", 1]])
        self.assertEqual(output["depth"], 0)

    def test_mutable_ownership(self):
        value = {"nested": [1]}
        state, stack = {}, []
        with patch.object(core, "solve", return_value=value):
            event = api._execute({"op": "put", "key": "x", "input": []}, state, stack)
        event["ok"]["nested"].append(2)
        value["nested"].append(3)
        api._execute({"op": "begin"}, state, stack)
        state["x"]["nested"].append(4)
        api._execute({"op": "rollback"}, state, stack)
        self.assertEqual(state, {"x": {"nested": [1]}})
        for command in [{"op": "get", "key": "x"}, {"op": "list"}]:
            returned = api._execute(command, state, stack)["ok"]
            returned.clear()
            self.assertEqual(state, {"x": {"nested": [1]}})

    def test_run_isolation_and_unicode_sort(self):
        output = journal([{"op": "put", "key": key, "input": [], "id": key}
                          for key in ["é", "z", "", "中", "A"]])
        self.assertEqual(output["state"], [[key, 0] for key in ["", "A", "z", "é", "中"]])
        self.assertEqual(journal([{"op": "begin", "id": "é"}]),
                         {"events": [{"ok": 1}], "state": [], "depth": 1})
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})


if __name__ == "__main__":
    unittest.main()
