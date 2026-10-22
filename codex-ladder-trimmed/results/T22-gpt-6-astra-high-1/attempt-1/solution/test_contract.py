import dataclasses
import itertools
import json
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


class AlgorithmTests(unittest.TestCase):
    def test_small_interval_combinations(self):
        intervals = list(itertools.product(range(-2, 3), repeat=2))
        for rows in itertools.product(intervals, repeat=3):
            expected = sum(
                sum(start <= x < end for start, end in rows) % 2
                for x in range(-2, 2)
            )
            self.assertEqual(core.solve(rows), expected, rows)

    def test_large_and_empty(self):
        self.assertEqual(core.solve([]), 0)
        self.assertEqual(core.solve([[-10**50, 10**50]]), 2 * 10**50)
        self.assertEqual(core.solve([[0, 10], [0, 10]]), 0)

    def test_pipeline_contract(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([f.name for f in dataclasses.fields(model.Result)], ["value"])
        rows = [[0, 3], [1, 2]]
        original = deepcopy(rows)
        result = service.compute(rows)
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, 2)
        self.assertEqual(rows, original)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.value = 3
        for value in (None, True, 0, 1.5, "雪", [], [1, {"a": [False]}]):
            with patch.object(core, "solve", return_value=value):
                self.assertEqual(json.loads(render.present(service.compute([]))), value)


class JournalTests(unittest.TestCase):
    def test_state_and_nested_transactions(self):
        result = journal([
            {"op": "put", "key": "", "input": [[0, 3]]},
            {"op": "begin"},
            {"op": "put", "key": "雪", "input": [[0, 4]]},
            {"op": "begin"},
            {"op": "delete", "key": ""},
            {"op": "commit"},
            {"op": "list"},
            {"op": "rollback"},
            {"op": "list"},
            {"op": "get", "key": "雪"},
            {"op": "delete", "key": "雪"},
            {"op": "commit"},
            {"op": "rollback"},
        ])
        self.assertEqual(result, {
            "events": [{"ok": 3}, {"ok": 1}, {"ok": 4}, {"ok": 2},
                       {"ok": 3}, {"ok": 1}, {"ok": [["雪", 4]]}, {"ok": 0},
                       {"ok": [["", 3]]}, {"error": "missing"},
                       {"error": "missing"}, {"error": "transaction"},
                       {"error": "transaction"}],
            "state": [["", 3]], "depth": 0,
        })

    def test_validation_is_atomic(self):
        invalid = [None, [], 2, True, "put", {}, {"op": []}, {"op": {}},
                   {"op": "unknown"}, {"op": "put", "key": "x"},
                   {"op": "put", "input": []}, {"op": "get"},
                   {"op": "delete", "key": None}, {"op": "expect", "key": "x"},
                   {"op": "expect", "key": 1, "value": 0}]
        invalid += [{"op": "begin", "id": value} for value in (None, 0, True, [], {})]
        result = journal([{"op": "begin"}] + invalid + [{"op": "list"}])
        self.assertEqual(result["events"], [{"ok": 1}] +
                         [{"error": "command"}] * len(invalid) + [{"ok": []}])
        self.assertEqual(result["state"], [])
        self.assertEqual(result["depth"], 1)

    def test_expect_and_sorting(self):
        result = journal([
            *({"op": "put", "key": key, "input": [[0, 1]]} for key in ["雪", "z", "", "A"]),
            {"op": "expect", "key": "", "value": True},
            {"op": "expect", "key": "absent", "value": None},
            {"op": "expect", "key": "z", "value": 0},
        ])
        self.assertEqual(result["state"], [["", 1], ["A", 1], ["z", 1], ["雪", 1]])
        self.assertEqual(result["events"][-3:], [{"ok": True},
                         {"error": "expectation"}, {"error": "expectation"}])

    def test_cache_survives_rollback_and_replays_controls(self):
        begin = {"op": "begin", "id": "b"}
        put = {"op": "put", "key": "x", "input": [[0, 2]], "id": "p"}
        rollback = {"op": "rollback", "id": "r"}
        result = journal([begin, begin, put, rollback, put, rollback,
                          {"op": "get", "key": "x"}, begin])
        self.assertEqual(result, {"events": [
            {"ok": 1}, {"ok": 1}, {"ok": 2}, {"ok": 0},
            {"ok": 2}, {"ok": 0}, {"error": "missing"}, {"ok": 1}],
            "state": [], "depth": 0})

    def test_identity_and_validation_order(self):
        result = journal([
            {"op": "list", "id": "", "extra": {"x": True, "y": [0]}},
            {"extra": {"y": [False], "x": 1}, "id": "", "op": "list"},
            {"op": "list", "id": ""},
            {"id": "", "op": "put"},
            {"op": "begin", "key": None, "input": None},
        ])
        self.assertEqual(result["events"], [{"ok": []}, {"ok": []},
                         {"error": "id-conflict"}, {"error": "id-conflict"}, {"ok": 1}])

    def test_failures_do_not_reserve_ids_and_runs_reset(self):
        result = journal([
            {"op": "get", "key": "x", "id": "a"},
            {"op": "put", "key": "x", "input": [[0, 1]], "id": "a"},
            {"op": "expect", "key": "x", "value": 2, "id": "b"},
            {"op": "begin", "id": "b"},
            {"op": "put", "id": "c"},
            {"op": "commit", "id": "c"},
            {"op": "rollback", "id": "d"},
            {"op": "list", "id": "d"},
        ])
        self.assertEqual(result["events"], [
            {"error": "missing"}, {"ok": 1}, {"error": "expectation"},
            {"ok": 1}, {"error": "command"}, {"ok": 0},
            {"error": "transaction"}, {"ok": [["x", 1]]}])
        self.assertEqual(journal([{ "op": "list", "id": "a"}]),
                         {"events": [{"ok": []}], "state": [], "depth": 0})

    def test_mutable_values_and_cached_list_history(self):
        value = {"nested": [1, {"x": None}]}
        first = {"op": "put", "key": "x", "input": [], "id": "p"}
        listing = {"op": "list", "id": "l"}
        with patch.object(core, "solve", side_effect=[value, [2]]):
            result = journal([first, listing, {"op": "begin"},
                              {"op": "put", "key": "x", "input": []},
                              listing, {"op": "rollback"}, first])
        self.assertEqual(result["events"][0], {"ok": value})
        self.assertEqual(result["events"][4], {"ok": [["x", value]]})
        self.assertEqual(result["state"], [["x", value]])
        # Exercise the internal ownership boundaries before serialization.
        state, stack = {}, []
        with patch.object(core, "solve", return_value=value):
            event = api._execute(first, state, stack)
        event["ok"]["nested"].append(9)
        self.assertEqual(state["x"], value)
        api._execute({"op": "begin"}, state, stack)
        state["x"]["nested"].append(8)
        self.assertEqual(stack[0]["x"], value)
        api._execute({"op": "rollback"}, state, stack)
        self.assertEqual(state["x"], value)


if __name__ == "__main__":
    unittest.main()
