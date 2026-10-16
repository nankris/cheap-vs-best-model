import dataclasses
from decimal import localcontext
from fractions import Fraction
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


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_result_and_json_types(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in dataclasses.fields(model.Result)], ["value"])
        for value in (None, True, 12, 1.5, "你好", [], [None, {"x": [1]}]):
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIsInstance(result, model.Result)
                self.assertEqual(result.value, value)
                self.assertEqual(json.loads(render.present(result)), value)
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    result.value = 1

    def test_money_and_rounding(self):
        cases = {"1.005": 100, "1.015": 102, "-1.005": -100,
                 "-1.015": -102, "0.005": 0, "-0.005": 0,
                 "9.999": 1000, "1e-1000": 0, "1e3": 100000}
        for value, cents in cases.items():
            self.assertEqual(core.Money.parse(value).cents, cents)
        self.assertEqual(core.Money(10) + core.Money(-3), core.Money(7))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            core.Money(0).cents = 1
        self.assertEqual(core.solve([]), "0.00")
        self.assertEqual(core.solve(["-0.000", "0.005"]), "0.00")
        self.assertEqual(core.solve(["0.005", "0.005"]), "0.00")
        self.assertEqual(core.solve(["-0.015"]), "-0.02")

    def test_precision_and_order_independence(self):
        rows = ["123456789012345678901234567890.125", "-123456789012345678901234567890", "0.015"]
        with localcontext() as context:
            context.prec = 2
            for permutation in itertools.permutations(rows):
                self.assertEqual(core.solve(permutation), "0.14")

    def test_rounding_against_exact_rational_reference(self):
        rng = random.Random(2048)
        for _ in range(1000):
            coefficient = rng.randrange(-10**40, 10**40)
            scale = rng.randrange(0, 50)
            value = f"{coefficient}e-{scale}"
            expected = round(Fraction(coefficient * 100, 10**scale))
            self.assertEqual(core.Money.parse(value).cents, expected)


class JournalTests(unittest.TestCase):
    def test_basic_operations_and_unicode_sort(self):
        result = journal([
            {"op": "get", "key": ""},
            {"op": "put", "key": "é", "input": ["1.015"]},
            {"op": "put", "key": "", "input": []},
            {"op": "put", "key": "Z", "input": ["-2"]},
            {"op": "list"},
            {"op": "expect", "key": "é", "value": "1.02"},
            {"op": "expect", "key": "é", "value": 1.02},
            {"op": "delete", "key": "Z"},
            {"op": "delete", "key": "Z"},
        ])
        self.assertEqual(result, {
            "events": [{"error": "missing"}, {"ok": "1.02"}, {"ok": "0.00"},
                       {"ok": "-2.00"}, {"ok": [["", "0.00"], ["Z", "-2.00"], ["é", "1.02"]]},
                       {"ok": True}, {"error": "expectation"}, {"ok": "-2.00"}, {"error": "missing"}],
            "state": [["", "0.00"], ["é", "1.02"]], "depth": 0,
        })

    def test_nested_transactions(self):
        result = journal([
            {"op": "commit"}, {"op": "rollback"},
            {"op": "put", "key": "a", "input": ["1"]},
            {"op": "begin"},
            {"op": "put", "key": "a", "input": ["2"]},
            {"op": "begin"}, {"op": "delete", "key": "a"},
            {"op": "commit"}, {"op": "rollback"}, {"op": "begin"},
        ])
        self.assertEqual(result["events"], [
            {"error": "transaction"}, {"error": "transaction"}, {"ok": "1.00"},
            {"ok": 1}, {"ok": "2.00"}, {"ok": 2}, {"ok": "2.00"},
            {"ok": 1}, {"ok": 0}, {"ok": 1},
        ])
        self.assertEqual(result["state"], [["a", "1.00"]])
        self.assertEqual(result["depth"], 1)

    def test_invalid_commands_are_atomic(self):
        malformed = [None, [], 1, "get", {}, {"op": []}, {"op": {}},
                     {"op": "unknown"}, {"op": "put", "key": "a"},
                     {"op": "put", "input": []}, {"op": "get"},
                     {"op": "delete", "key": None}, {"op": "expect", "key": "a"}]
        malformed += [{"op": op, "key": key, "input": [], "value": None}
                      for op in ("put", "get", "delete", "expect")
                      for key in (None, 1, True, [], {})]
        malformed += [{"op": "begin", "id": identifier} for identifier in (None, 0, False, [], {})]
        result = journal([{"op": "begin"}, {"op": "put", "key": "a", "input": []}]
                         + malformed + [{"op": "list"}])
        self.assertEqual(result["events"][2:-1], [{"error": "command"}] * len(malformed))
        self.assertEqual(result["state"], [["a", "0.00"]])
        self.assertEqual(result["depth"], 1)

    def test_replay_transactions_without_side_effects(self):
        result = journal([
            {"op": "begin", "id": "b"}, {"op": "begin", "id": "b"},
            {"op": "put", "key": "x", "input": ["1"], "id": "p"},
            {"op": "rollback", "id": "r"},
            {"op": "put", "key": "x", "input": ["1"], "id": "p"},
            {"op": "begin"}, {"op": "rollback", "id": "r"},
            {"op": "commit", "id": "c"}, {"op": "begin"},
            {"op": "commit", "id": "c"},
        ])
        self.assertEqual(result["events"], [{"ok": 1}, {"ok": 1}, {"ok": "1.00"},
            {"ok": 0}, {"ok": "1.00"}, {"ok": 1}, {"ok": 0}, {"ok": 0}, {"ok": 1}, {"ok": 0}])
        self.assertEqual(result["state"], [])
        self.assertEqual(result["depth"], 1)

    def test_identity_extras_equality_and_validation_order(self):
        result = journal([
            {"op": "list", "id": "", "extra": {"a": True, "b": [0]}},
            {"extra": {"b": [False], "a": 1}, "id": "", "op": "list"},
            {"op": "list", "id": ""}, {"id": ""},
            {"op": [], "id": ""}, {"op": "put", "id": ""},
            {"op": "list", "id": None},
            {"op": "begin", "key": [], "value": 3},
        ])
        self.assertEqual(result["events"], [{"ok": []}, {"ok": []}]
                         + [{"error": "id-conflict"}] * 4
                         + [{"error": "command"}, {"ok": 1}])

    def test_failures_do_not_reserve_ids(self):
        failures = [{"op": "get", "key": "x"}, {"op": "delete", "key": "x"},
                    {"op": "expect", "key": "x", "value": None},
                    {"op": "commit"}, {"op": "rollback"}, {"op": "put"}]
        for failure in failures:
            result = journal([dict(failure, id="retry"), {"op": "begin", "id": "retry"}])
            self.assertIn("error", result["events"][0])
            self.assertEqual(result["events"][1], {"ok": 1})

    def test_read_and_delete_replay_original_results(self):
        result = journal([
            {"op": "put", "key": "x", "input": ["1"]},
            {"op": "get", "key": "x", "id": "g"}, {"op": "list", "id": "l"},
            {"op": "delete", "key": "x", "id": "d"},
            {"op": "put", "key": "x", "input": ["2"]},
            {"op": "get", "key": "x", "id": "g"}, {"op": "list", "id": "l"},
            {"op": "delete", "key": "x", "id": "d"},
        ])
        self.assertEqual(result["events"][5:], [{"ok": "1.00"}, {"ok": [["x", "1.00"]]}, {"ok": "1.00"}])
        self.assertEqual(result["state"], [["x", "2.00"]])

    def test_generic_values_expect_and_ownership(self):
        source = {"nested": [1, None]}
        commands = [{"op": "put", "key": "x", "input": [], "id": "p"},
                    {"op": "begin"}, {"op": "delete", "key": "x"},
                    {"op": "rollback"}, {"op": "get", "key": "x", "id": "g"},
                    {"op": "get", "key": "x", "id": "g"},
                    {"op": "put", "key": "x", "input": [], "id": "p"},
                    {"op": "expect", "key": "x", "value": {"nested": [True, None]}},
                    {"op": "list"}]
        original = json.loads(json.dumps(commands))
        payload = json.dumps(commands)
        captured = []
        dumps = json.dumps

        def capture(value, *args, **kwargs):
            if isinstance(value, dict) and "events" in value:
                captured.append(value)
            return dumps(value, *args, **kwargs)

        with patch.object(core, "solve", return_value=source), patch.object(api.json, "dumps", side_effect=capture):
            result = json.loads(api.run(payload))
        self.assertEqual(result["events"][7], {"ok": True})
        self.assertEqual(commands, original)
        raw = captured[0]
        raw["events"][0]["ok"]["nested"].append(2)
        raw["events"][4]["ok"]["nested"].append(3)
        raw["events"][8]["ok"][0][1]["nested"].append(4)
        self.assertEqual(raw["state"], [["x", source]])
        self.assertEqual(raw["events"][5], {"ok": source})
        self.assertEqual(raw["events"][6], {"ok": source})
        self.assertEqual(source, {"nested": [1, None]})

    def test_no_state_or_cache_survives_calls(self):
        journal([{"op": "put", "key": "x", "input": [], "id": "id"}, {"op": "begin"}])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        self.assertEqual(journal([{"op": "list", "id": "id"}]),
                         {"events": [{"ok": []}], "state": [], "depth": 0})


if __name__ == "__main__":
    unittest.main()
