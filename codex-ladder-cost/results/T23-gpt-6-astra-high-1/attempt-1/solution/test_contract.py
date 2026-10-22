import json
import random
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from unittest.mock import patch

import api
import core
import model
import render
import service


def run(commands):
    return json.loads(api.run(json.dumps(commands)))


class AlgorithmTests(unittest.TestCase):
    def test_rounding_and_totals(self):
        cases = [
            ([], "0.00"),
            (["0.005", "0.005"], "0.00"),
            (["0.015", "0.015"], "0.04"),
            (["-0.005"], "0.00"),
            (["-0.015"], "-0.02"),
            (["1.225", "1.235", "-2.46"], "0.00"),
            (["1e2", "-.009", ".0050001"], "100.00"),
            (["-0", "0e999999", "1e-999999"], "0.00"),
        ]
        for rows, expected in cases:
            with self.subTest(rows=rows):
                original = deepcopy(rows)
                self.assertEqual(core.solve(rows), expected)
                self.assertEqual(core.solve(list(reversed(rows))), expected)
                self.assertEqual(rows, original)

    def test_independent_of_decimal_context_and_digit_limits(self):
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(core.solve(["123456789012345678901234567890.125"]),
                             "123456789012345678901234567890.12")
            self.assertEqual(core.solve(["1e5000"]), "1" + "0" * 5000 + ".00")

    def test_random_rounding_against_decimal(self):
        generator = random.Random(42)
        with localcontext() as context:
            context.prec = 100
            for _ in range(1000):
                value = f"{generator.randrange(-10**15, 10**15)}e{generator.randrange(-20, 10)}"
                expected = int(Decimal(value).quantize(Decimal(".01"),
                                                       rounding=ROUND_HALF_EVEN) * 100)
                self.assertEqual(core.Money.parse(value).cents, expected)

    def test_money(self):
        amount = core.Money.parse("1.005") + core.Money.parse("2.015")
        self.assertEqual(amount, core.Money(302))
        with self.assertRaises(FrozenInstanceError):
            amount.cents = 0
        self.assertIs(amount.__add__(1), NotImplemented)

    def test_result_pipeline(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute(["1.015"])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, "1.02")
        self.assertEqual(json.loads(render.present(result)), "1.02")
        with self.assertRaises(FrozenInstanceError):
            result.value = None
        for value in [None, False, 0, 1.5, "é", [1, {"a": [True]}], {"a": None}]:
            with patch.object(core, "solve", return_value=value):
                self.assertEqual(json.loads(render.present(service.compute([]))), value)


class JournalTests(unittest.TestCase):
    def test_basic_operations_and_unicode_sort(self):
        output = run([
            {"op": "put", "key": "é", "input": ["1.005"]},
            {"op": "put", "key": "", "input": []},
            {"op": "put", "key": "Z", "input": ["-.015"]},
            {"op": "list"},
            {"op": "get", "key": "é"},
            {"op": "expect", "key": "é", "value": "1.00"},
            {"op": "expect", "key": "absent", "value": None},
            {"op": "delete", "key": "é"},
            {"op": "get", "key": "é"},
            {"op": "delete", "key": "é"},
        ])
        self.assertEqual(output, {
            "events": [{"ok": "1.00"}, {"ok": "0.00"}, {"ok": "-0.02"},
                       {"ok": [["", "0.00"], ["Z", "-0.02"], ["é", "1.00"]]},
                       {"ok": "1.00"}, {"ok": True}, {"error": "expectation"},
                       {"ok": "1.00"}, {"error": "missing"}, {"error": "missing"}],
            "state": [["", "0.00"], ["Z", "-0.02"]], "depth": 0,
        })

    def test_nested_transactions(self):
        output = run([
            {"op": "begin"}, {"op": "put", "key": "x", "input": ["1"]},
            {"op": "begin"}, {"op": "put", "key": "x", "input": ["2"]},
            {"op": "expect", "key": "x", "value": "wrong"},
            {"op": "commit"}, {"op": "get", "key": "x"},
            {"op": "rollback"}, {"op": "get", "key": "x"},
            {"op": "commit"}, {"op": "rollback"}, {"op": "begin"},
        ])
        self.assertEqual(output["events"], [
            {"ok": 1}, {"ok": "1.00"}, {"ok": 2}, {"ok": "2.00"},
            {"error": "expectation"}, {"ok": 1}, {"ok": "2.00"}, {"ok": 0},
            {"error": "missing"}, {"error": "transaction"},
            {"error": "transaction"}, {"ok": 1},
        ])
        self.assertEqual(output["state"], [])
        self.assertEqual(output["depth"], 1)

    def test_replay_survives_rollback_and_does_not_execute(self):
        put = {"op": "put", "key": "x", "input": ["1"], "id": "p"}
        output = run([
            {"op": "begin", "id": "b"}, {"op": "begin", "id": "b"},
            put, {"op": "list", "id": "l"},
            {"op": "rollback", "id": "r"}, put,
            {"op": "list", "id": "l"}, {"op": "rollback", "id": "r"},
            {"op": "begin", "id": "b"}, {"op": "list"},
        ])
        self.assertEqual(output["events"], [
            {"ok": 1}, {"ok": 1}, {"ok": "1.00"}, {"ok": [["x", "1.00"]]},
            {"ok": 0}, {"ok": "1.00"}, {"ok": [["x", "1.00"]]},
            {"ok": 0}, {"ok": 1}, {"ok": []},
        ])
        self.assertEqual(output["state"], [])
        self.assertEqual(output["depth"], 0)

    def test_identity_and_validation_order(self):
        output = run([
            {"op": "list", "id": "", "extra": {"a": True, "b": [0]}},
            {"extra": {"b": [False], "a": 1}, "id": "", "op": "list"},
            {"op": "list", "id": "", "extra": {}},
            {"op": "put", "id": ""},
            {"op": [], "id": ""},
            {"op": "list", "id": None},
        ])
        self.assertEqual(output["events"], [
            {"ok": []}, {"ok": []}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "id-conflict"},
            {"error": "command"},
        ])

    def test_failures_do_not_reserve_ids(self):
        for failure in [
            {"op": "put"}, {"op": "get", "key": "x"},
            {"op": "delete", "key": "x"}, {"op": "commit"},
            {"op": "rollback"}, {"op": "expect", "key": "x", "value": None},
        ]:
            output = run([dict(failure, id="retry"), {"op": "begin", "id": "retry"}])
            self.assertIn("error", output["events"][0])
            self.assertEqual(output["events"][1], {"ok": 1})

    def test_malformed_commands_are_atomic(self):
        malformed = [None, [], 1, True, "put", {}, {"op": []}, {"op": {}},
                     {"op": "unknown"}, {"op": "put", "key": "x"},
                     {"op": "expect", "key": "x"}]
        for op in ["put", "get", "delete", "expect"]:
            for key in [None, 1, True, [], {}]:
                malformed.append({"op": op, "key": key, "input": [], "value": None})
        for op in ["begin", "commit", "rollback", "list", "put"]:
            for identifier in [None, 1, False, [], {}]:
                malformed.append({"op": op, "id": identifier, "key": "x", "input": []})
        journal = api._Journal()
        journal.command({"op": "put", "key": "x", "input": ["1"], "id": "p"})
        journal.command({"op": "begin"})
        before = deepcopy((journal.state, journal.stack, journal.cache))
        for command in malformed:
            self.assertEqual(journal.command(command), {"error": "command"})
            self.assertEqual((journal.state, journal.stack, journal.cache), before)

    def test_mutable_ownership_and_python_equality(self):
        journal = api._Journal()
        command = {"op": "put", "key": "x", "input": [], "id": "p", "extra": [1]}
        original = deepcopy(command)
        with patch.object(core, "solve", return_value=[{"nested": [1]}]):
            event = journal.command(command)
        event["ok"][0]["nested"].append(2)
        command["extra"].append(2)
        replay = journal.command(original)
        self.assertEqual(replay, {"ok": [{"nested": [1]}]})
        replay["ok"].clear()
        journal.command({"op": "begin"})
        journal.state["x"][0]["nested"].append(3)
        journal.command({"op": "rollback"})
        self.assertEqual(journal.state["x"], [{"nested": [1]}])
        self.assertEqual(journal.command({"op": "expect", "key": "x",
                                          "value": [{"nested": [True]}]}), {"ok": True})
        for op in ["get", "list", "delete"]:
            event = journal.command({"op": op, "key": "x", "id": op})
            event["ok"].clear()
            self.assertTrue(journal.command({"op": op, "key": "x", "id": op})["ok"])

    def test_pipeline_for_put_and_invocation_isolation(self):
        commands = [{"op": "put", "key": "x", "input": [], "id": "p"}]
        for value in [None, False, 0, [1, {"x": 2}]]:
            with patch.object(core, "solve", return_value=value) as solve:
                self.assertEqual(run(commands)["state"], [["x", value]])
                solve.assert_called_once_with([])
        self.assertEqual(run([]), {"events": [], "state": [], "depth": 0})
        self.assertEqual(run([{"op": "begin", "id": "p"}])["depth"], 1)
        self.assertEqual(run([{"op": "get", "key": "x"}])["events"],
                         [{"error": "missing"}])


if __name__ == "__main__":
    unittest.main()
