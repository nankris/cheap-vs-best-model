import copy
from dataclasses import FrozenInstanceError, fields
import itertools
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
    def test_examples_and_ownership(self):
        for rows, expected in [
            ([], []),
            ([["a", "a"]], None),
            ([["a", "b"], ["b", "a"]], None),
            ([["b", "c"], ["a", "c"], ["a", "c"]], ["a", "b", "c"]),
            ([["z", "a"], ["b", "c"]], ["b", "c", "z", "a"]),
            ([["é", "😀"], ["", "é"]], ["", "é", "😀"]),
        ]:
            with self.subTest(rows=rows):
                original = copy.deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(rows, original)

    def test_against_exhaustive_ordering_oracle(self):
        rng = random.Random(314159)
        nodes = ["", "a", "b", "é", "😀"]
        pairs = list(itertools.product(nodes, repeat=2))
        for _ in range(200):
            rows = [list(rng.choice(pairs)) for _ in range(rng.randrange(12))]
            mentioned = sorted({node for edge in rows for node in edge})
            expected = None
            for order in itertools.permutations(mentioned):
                positions = {node: i for i, node in enumerate(order)}
                if all(positions[a] < positions[b] for a, b in rows):
                    expected = list(order)
                    break
            self.assertEqual(core.solve(rows), expected, rows)

    def test_result_and_independent_pipeline(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([["b", "c"]])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, ["b", "c"])
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        for value in [None, [], 0, 1.5, True, "é", {"x": [False, None]}]:
            with patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIsInstance(result, model.Result)
                self.assertEqual(result.value, value)
                rendered = render.present(result)
                self.assertIsInstance(rendered, str)
                self.assertEqual(json.loads(rendered), value)


class JournalTests(unittest.TestCase):
    def test_basic_operations_and_sorted_state(self):
        commands = [
            {"op": "put", "key": "é", "input": [["a", "b"]]},
            {"op": "put", "key": "", "input": []},
            {"op": "put", "key": "z", "input": [["a", "a"]]},
            {"op": "get", "key": "z"},
            {"op": "expect", "key": "z", "value": None},
            {"op": "expect", "key": "absent", "value": None},
            {"op": "list"},
            {"op": "delete", "key": "é"},
            {"op": "get", "key": "é"},
            {"op": "delete", "key": "é"},
        ]
        original = copy.deepcopy(commands)
        self.assertEqual(journal(commands), {
            "events": [
                {"ok": ["a", "b"]}, {"ok": []}, {"ok": None},
                {"ok": None}, {"ok": True}, {"error": "expectation"},
                {"ok": [["", []], ["z", None], ["é", ["a", "b"]]]},
                {"ok": ["a", "b"]}, {"error": "missing"}, {"error": "missing"},
            ], "state": [["", []], ["z", None]], "depth": 0,
        })
        self.assertEqual(commands, original)

    def test_nested_transactions(self):
        commands = [
            {"op": "commit"}, {"op": "rollback"}, {"op": "begin"},
            {"op": "put", "key": "a", "input": []}, {"op": "begin"},
            {"op": "delete", "key": "a"}, {"op": "rollback"},
            {"op": "get", "key": "a"}, {"op": "begin"},
            {"op": "put", "key": "b", "input": []}, {"op": "commit"},
            {"op": "expect", "key": "a", "value": False},
            {"op": "rollback"}, {"op": "list"}, {"op": "begin"},
        ]
        self.assertEqual(journal(commands), {
            "events": [
                {"error": "transaction"}, {"error": "transaction"}, {"ok": 1},
                {"ok": []}, {"ok": 2}, {"ok": []}, {"ok": 1}, {"ok": []},
                {"ok": 2}, {"ok": []}, {"ok": 1}, {"error": "expectation"},
                {"ok": 0}, {"ok": []}, {"ok": 1},
            ], "state": [], "depth": 1,
        })

    def test_malformed_commands_are_atomic(self):
        malformed = [
            None, [], "put", 1, True, {}, {"op": []}, {"op": {}},
            {"op": "unknown"}, {"op": "put", "key": "x"},
            {"op": "put", "input": []}, {"op": "get"}, {"op": "delete"},
            {"op": "expect", "key": "x"}, {"op": "expect", "value": []},
        ]
        malformed += [{"op": op, "key": key, "input": [], "value": []}
                      for op in ["put", "get", "delete", "expect"]
                      for key in [None, 1, True, [], {}]]
        malformed += [{"op": op, "id": bad_id}
                      for op in ["begin", "commit", "rollback", "list"]
                      for bad_id in [None, 1, False, [], {}]]
        result = journal([
            {"op": "put", "key": "x", "input": []}, {"op": "begin"},
            *malformed, {"op": "list", "key": None, "input": "ignored"},
        ])
        self.assertEqual(result["events"][2:-1], [{"error": "command"}] * len(malformed))
        self.assertEqual(result["events"][-1], {"ok": [["x", []]]})
        self.assertEqual(result["state"], [["x", []]])
        self.assertEqual(result["depth"], 1)

    def test_identities_replay_and_validation_precedence(self):
        first = {"op": "put", "key": "x", "input": [], "id": "", "extra": {"a": 1, "b": [False]}}
        equivalent = {"id": "", "extra": {"b": [0], "a": True}, "input": [], "key": "x", "op": "put"}
        result = journal([
            first, {"op": "delete", "key": "x"}, equivalent,
            {"op": "put", "key": "x", "id": ""},
            {**first, "extra": None}, {**first, "id": None},
            {"op": "get", "key": "x", "id": "retry"},
            {"op": "put", "key": "y", "input": [], "id": "retry"},
        ])
        self.assertEqual(result["events"], [
            {"ok": []}, {"ok": []}, {"ok": []}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "command"},
            {"error": "missing"}, {"ok": []},
        ])
        self.assertEqual(result["state"], [["y", []]])

    def test_cached_control_events_survive_rollback(self):
        begin = {"op": "begin", "id": "begin"}
        put = {"op": "put", "key": "x", "input": [], "id": "put"}
        listing = {"op": "list", "id": "list"}
        rollback = {"op": "rollback", "id": "rollback"}
        result = journal([begin, begin, put, listing, rollback, put, listing, rollback, begin])
        self.assertEqual(result, {
            "events": [{"ok": 1}, {"ok": 1}, {"ok": []}, {"ok": [["x", []]]},
                       {"ok": 0}, {"ok": []}, {"ok": [["x", []]]}, {"ok": 0}, {"ok": 1}],
            "state": [], "depth": 0,
        })

    def test_failed_ids_are_not_reserved_and_runs_reset(self):
        for failure in [
            {"op": "commit"}, {"op": "rollback"}, {"op": "get", "key": "x"},
            {"op": "delete", "key": "x"}, {"op": "expect", "key": "x", "value": []},
            {"op": "put", "key": "x"}, {"op": "invalid"},
        ]:
            result = journal([{**failure, "id": "same"}, {"op": "begin", "id": "same"}])
            self.assertIn("error", result["events"][0])
            self.assertEqual(result["events"][1], {"ok": 1})
        journal([{"op": "begin", "id": "x"}, {"op": "put", "key": "x", "input": []}])
        self.assertEqual(journal([{ "op": "list", "id": "x"}]),
                         {"events": [{"ok": []}], "state": [], "depth": 0})

    def test_pipeline_ownership_and_python_json_equality(self):
        mutable = {"items": [1, False]}
        with patch.object(core, "solve", return_value=mutable) as solve:
            result = journal([
                {"op": "put", "key": "x", "input": [], "id": "p"},
                {"op": "expect", "key": "x", "value": {"items": [True, 0]}},
                {"op": "begin"}, {"op": "get", "key": "x", "id": "g"},
                {"op": "delete", "key": "x"}, {"op": "rollback"},
                {"op": "put", "key": "x", "input": [], "id": "p"},
            ])
            solve.assert_called_once_with([])
        self.assertEqual(result["events"][1], {"ok": True})
        result["events"][0]["ok"]["items"].append(2)
        self.assertEqual(result["state"], [["x", mutable]])
        self.assertEqual(result["events"][-1], {"ok": mutable})
        self.assertEqual(mutable, {"items": [1, False]})


if __name__ == "__main__":
    unittest.main()
