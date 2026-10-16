import json
import random
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from unittest.mock import patch

import api
import core
import model
import render
import service


def journal(*commands):
    return json.loads(api.run(json.dumps(commands)))


def put(key, rows, **extra):
    return dict(op="put", key=key, input=rows, **extra)


class PipelineTests(unittest.TestCase):
    def test_result_and_render_contract(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        for value in (None, False, 0, 3.5, "雪", [], [1, None], {"a": True}):
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIsInstance(result, model.Result)
                self.assertEqual(result.value, value)
                self.assertIsInstance(render.present(result), str)
                self.assertEqual(json.loads(render.present(result)), value)
                with self.assertRaises(FrozenInstanceError):
                    result.value = None
                output = journal(put("", []))
                self.assertEqual(output["events"], [{"ok": value}])
                self.assertEqual(output["state"], [["", value]])

    def test_interval_union(self):
        rows = [[8, 6], [2, 1], [4, 3], [2, 2], [-3, -5], [-2, 0], [20, 20]]
        original = deepcopy(rows)
        self.assertEqual(core.solve(rows), [[-5, 4], [6, 8], [20, 20]])
        self.assertEqual(rows, original)
        self.assertEqual(core.solve([]), [])
        rng = random.Random(17)
        for _ in range(200):
            rows = [[rng.randint(-20, 20), rng.randint(-20, 20)]
                    for _ in range(rng.randrange(12))]
            points = sorted({point for a, b in rows
                             for point in range(min(a, b), max(a, b) + 1)})
            expected = []
            for point in points:
                if expected and point == expected[-1][1] + 1:
                    expected[-1][1] = point
                else:
                    expected.append([point, point])
            self.assertEqual(core.solve(rows), expected)


class JournalTests(unittest.TestCase):
    def test_basic_commands_and_order(self):
        output = journal(
            put("雪", [[3, 1]]), put("", []), put("a", [[9, 9]]),
            {"op": "list"}, {"op": "get", "key": "雪"},
            {"op": "expect", "key": "雪", "value": [[1, 3]]},
            {"op": "expect", "key": "absent", "value": None},
            {"op": "delete", "key": "a"}, {"op": "delete", "key": "a"},
            {"op": "get", "key": "a"})
        self.assertEqual(output, {
            "events": [{"ok": [[1, 3]]}, {"ok": []}, {"ok": [[9, 9]]},
                       {"ok": [["", []], ["a", [[9, 9]]], ["雪", [[1, 3]]]]},
                       {"ok": [[1, 3]]}, {"ok": True}, {"error": "expectation"},
                       {"ok": [[9, 9]]}, {"error": "missing"}, {"error": "missing"}],
            "state": [["", []], ["雪", [[1, 3]]]], "depth": 0})

    def test_nested_transactions(self):
        output = journal(
            {"op": "commit"}, {"op": "rollback"}, put("x", [[1, 1]]),
            {"op": "begin"}, put("x", [[2, 2]]), {"op": "begin"},
            {"op": "delete", "key": "x"}, {"op": "commit"},
            {"op": "expect", "key": "x", "value": []}, {"op": "rollback"})
        self.assertEqual(output["events"], [
            {"error": "transaction"}, {"error": "transaction"}, {"ok": [[1, 1]]},
            {"ok": 1}, {"ok": [[2, 2]]}, {"ok": 2}, {"ok": [[2, 2]]},
            {"ok": 1}, {"error": "expectation"}, {"ok": 0}])
        self.assertEqual(output["state"], [["x", [[1, 1]]]])
        self.assertEqual(output["depth"], 0)

    def test_malformed_commands_are_atomic(self):
        invalid = [None, [], 1, "put", {}, {"op": []}, {"op": {}},
                   {"op": "unknown"}, {"op": "put", "key": "x"},
                   {"op": "put", "input": []}, {"op": "get"},
                   {"op": "delete", "key": None}, {"op": "expect", "key": "x"},
                   {"op": "expect", "value": []}, {"op": "get", "key": 1}]
        invalid += [{"op": "begin", "id": value} for value in (None, 1, False, [], {})]
        output = journal(put("x", []), {"op": "begin"}, *invalid,
                         {"op": "rollback"}, {"op": "get", "key": "x"})
        self.assertEqual(output["events"][2:-2], [{"error": "command"}] * len(invalid))
        self.assertEqual(output["events"][-2:], [{"ok": 0}, {"ok": []}])
        self.assertEqual(output["state"], [["x", []]])
        self.assertEqual(output["depth"], 0)

    def test_identity_equality_and_validation_precedence(self):
        first = put("x", [[0, 1]], id="", extra={"a": [True], "b": 0})
        equal = {"extra": {"b": False, "a": [1]}, "id": "", "input": [[False, True]],
                 "key": "x", "op": "put"}
        output = journal(first, {"op": "delete", "key": "x"}, equal,
                         {"id": "", "op": "put"}, dict(first, extra=None),
                         {"op": "list", "key": None, "input": 42})
        self.assertEqual(output["events"], [
            {"ok": [[0, 1]]}, {"ok": [[0, 1]]}, {"ok": [[0, 1]]},
            {"error": "id-conflict"}, {"error": "id-conflict"}, {"ok": []}])
        self.assertEqual(output["state"], [])

    def test_failures_do_not_reserve_ids(self):
        failures = [{"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
                    {"op": "expect", "key": "x", "value": []},
                    {"op": "commit"}, {"op": "rollback"}, {"op": "put"}]
        for failure in failures:
            with self.subTest(failure=failure):
                output = journal(dict(failure, id="retry"), put("x", [], id="retry"))
                self.assertIn("error", output["events"][0])
                self.assertEqual(output["events"][1], {"ok": []})
                self.assertEqual(output["state"], [["x", []]])

    def test_cache_survives_rollback(self):
        command = put("x", [[1, 1]], id="saved")
        output = journal({"op": "begin"}, command, {"op": "rollback"}, command)
        self.assertEqual(output["events"][-1], {"ok": [[1, 1]]})
        self.assertEqual(output["state"], [])
        self.assertEqual(output["depth"], 0)

    def test_transaction_replays_have_no_effect(self):
        for op in ("begin", "commit", "rollback"):
            with self.subTest(op=op):
                command = {"op": op, "id": "transaction"}
                output = journal({"op": "begin"}, command, {"op": "begin"}, command)
                self.assertEqual(output["events"][1], output["events"][3])
                self.assertEqual(output["depth"], 3 if op == "begin" else 1)

    def test_read_and_delete_replays(self):
        for command in ({"op": "get", "key": "x"}, {"op": "list"},
                        {"op": "expect", "key": "x", "value": [[1, 1]]},
                        {"op": "delete", "key": "x"}):
            with self.subTest(command=command):
                command = dict(command, id="read")
                output = journal(put("x", [[1, 1]]), command, put("x", [[2, 2]]), command)
                self.assertEqual(output["events"][1], output["events"][3])
                self.assertEqual(output["state"], [["x", [[2, 2]]]])

    def test_python_expect_equality_and_run_reset(self):
        output = journal(put("x", [[0, 1]], id="x"),
                         {"op": "expect", "key": "x", "value": [[False, True]]},
                         {"op": "begin"})
        self.assertEqual(output["events"][1], {"ok": True})
        self.assertEqual(journal(), {"events": [], "state": [], "depth": 0})
        self.assertEqual(journal(put("y", [], id="x"))["state"], [["y", []]])

    def test_mutable_ownership_boundaries(self):
        state, stack = {}, []
        command = put("x", [[1, 2]])
        event = api._execute(command, state, stack)
        command["input"][0][0] = 99
        event["ok"][0][0] = 88
        self.assertEqual(state, {"x": [[1, 2]]})
        api._execute({"op": "begin"}, state, stack)
        state["x"][0][0] = 77
        self.assertEqual(stack, [{"x": [[1, 2]]}])
        api._execute({"op": "rollback"}, state, stack)
        read = api._execute({"op": "get", "key": "x"}, state, stack)
        listing = api._execute({"op": "list"}, state, stack)
        read["ok"][0][0] = 66
        listing["ok"][0][1][0][0] = 55
        self.assertEqual(state, {"x": [[1, 2]]})


if __name__ == "__main__":
    unittest.main()
