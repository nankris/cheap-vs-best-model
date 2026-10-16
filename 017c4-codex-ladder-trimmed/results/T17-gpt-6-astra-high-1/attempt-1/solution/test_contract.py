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


def put(key="k", amount="1", **extra):
    return {"op": "put", "key": key, "input": [["account", amount, "row"]], **extra}


class AlgorithmTests(unittest.TestCase):
    def test_exact_totals_deduplication_sorting_and_rounding(self):
        rows = [
            ["z", "1.005", "a"], ["z", "0.005", "b"],
            ["a", "999", "a"], ["a", "2.345", "c"],
            ["b", "2.355", "d"], ["c", "-2.345", "e"],
            ["d", "-2.355", "f"], ["e", "-0.005", "g"],
            ["f", "-0.000", "h"],
        ]
        original = deepcopy(rows)
        self.assertEqual(core.solve(rows), [
            ["a", "2.34"], ["b", "2.36"], ["c", "-2.34"],
            ["d", "-2.36"], ["e", "0.00"], ["f", "0.00"], ["z", "1.01"],
        ])
        self.assertEqual(rows, original)
        self.assertEqual(core.solve([]), [])

    def test_precision_and_cancellation(self):
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(core.solve([
                ["a", "123456789012345678901234567890.125", 1],
                ["a", "0.01", 2],
                ["b", "1E+70", 3], ["b", "0.015", 4], ["b", "-1E+70", 5],
            ]), [["a", "123456789012345678901234567890.14"], ["b", "0.02"]])

    def test_randomized_decimal_reference(self):
        rng = random.Random(103)
        with localcontext() as context:
            context.prec = 100
            for _ in range(150):
                rows = [[rng.choice(["", "a", "é"]),
                         str(Decimal(rng.randrange(-10**20, 10**20)).scaleb(-rng.randrange(8))),
                         rng.randrange(30)] for _ in range(50)]
                seen, balances = set(), {}
                for account, amount, row_id in rows:
                    if row_id not in seen:
                        seen.add(row_id)
                        balances[account] = balances.get(account, Decimal(0)) + Decimal(amount)
                expected = []
                for account, total in sorted(balances.items()):
                    rounded = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                    expected.append([account, "0.00" if rounded == 0 else format(rounded, "f")])
                self.assertEqual(core.solve(rows), expected)


class PipelineTests(unittest.TestCase):
    def test_result_contract(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([])
        self.assertIsInstance(result, model.Result)
        with self.assertRaises(FrozenInstanceError):
            result.value = 3

    def test_preserve_json_values_through_every_layer(self):
        for value in [None, False, 0, 1.5, "é", [], [1, {"a": [True]}], {"a": None}]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertIsInstance(result, model.Result)
                rendered = render.present(result)
                self.assertIsInstance(rendered, str)
                self.assertEqual(json.loads(rendered), value)
                journal = run([{"op": "put", "key": "", "input": []}])
                self.assertEqual(journal, {"events": [{"ok": value}], "state": [["", value]], "depth": 0})


class JournalTests(unittest.TestCase):
    def test_basic_commands_and_unicode_order(self):
        value = [["account", "1.00"]]
        result = run([put("é"), put(""), put("z"), {"op": "get", "key": "é"},
                      {"op": "expect", "key": "é", "value": value},
                      {"op": "expect", "key": "é", "value": None},
                      {"op": "delete", "key": "z"}, {"op": "delete", "key": "z"},
                      {"op": "get", "key": "missing"}, {"op": "list"}])
        self.assertEqual(result["events"], [{"ok": value}] * 4 + [
            {"ok": True}, {"error": "expectation"}, {"ok": value},
            {"error": "missing"}, {"error": "missing"}, {"ok": [["", value], ["é", value]]},
        ])
        self.assertEqual(result["state"], [["", value], ["é", value]])

    def test_nested_transactions_and_expectation_failure(self):
        commands = [put(), {"op": "begin"}, put(amount="2"), {"op": "begin"},
                    {"op": "delete", "key": "k"}, {"op": "rollback"},
                    {"op": "expect", "key": "k", "value": []}, {"op": "commit"},
                    {"op": "rollback"}, {"op": "commit"}]
        result = run(commands)
        self.assertEqual(result["state"], [["k", [["account", "2.00"]]]])
        self.assertEqual(result["depth"], 0)
        self.assertEqual(result["events"][5:], [{"ok": 1}, {"error": "expectation"},
                                               {"ok": 0}, {"error": "transaction"},
                                               {"error": "transaction"}])

    def test_malformed_commands_are_atomic_and_do_not_reserve_ids(self):
        invalid = [None, [], "put", 7, True, {}, {"op": []}, {"op": "unknown"},
                   {"op": "put", "key": "k"}, {"op": "put", "input": []},
                   {"op": "get"}, {"op": "delete", "key": False},
                   {"op": "expect", "key": "k"}, {"op": "expect", "key": [], "value": 1}]
        invalid += [{"op": "rollback", "id": value} for value in [None, False, 1, [], {}]]
        invalid += [{"op": "put", "id": "reusable", "key": "k"}]
        result = run([put(), {"op": "begin"}] + invalid + [{"op": "list", "id": "reusable"}])
        self.assertEqual(result["events"][2:-1], [{"error": "command"}] * len(invalid))
        self.assertEqual(result["state"], [["k", [["account", "1.00"]]]])
        self.assertEqual(result["depth"], 1)
        self.assertIn("ok", result["events"][-1])

    def test_cache_survives_rollback_and_replays_without_effects(self):
        begin = {"op": "begin", "id": "begin"}
        write = put(id="write")
        rollback = {"op": "rollback", "id": "rollback"}
        result = run([begin, begin, write, rollback, write, rollback, begin, {"op": "list"}])
        self.assertEqual(result, {"events": [
            {"ok": 1}, {"ok": 1}, {"ok": [["account", "1.00"]]}, {"ok": 0},
            {"ok": [["account", "1.00"]]}, {"ok": 0}, {"ok": 1}, {"ok": []},
        ], "state": [], "depth": 0})

    def test_cached_reads_and_deletes(self):
        listing = {"op": "list", "id": "list"}
        get = {"op": "get", "key": "k", "id": "get"}
        delete = {"op": "delete", "key": "k", "id": "delete"}
        result = run([put(), listing, get, delete, put(amount="2"), listing, get, delete])
        for old, replay in [(1, 5), (2, 6), (3, 7)]:
            self.assertEqual(result["events"][old], result["events"][replay])
        self.assertEqual(result["state"], [["k", [["account", "2.00"]]]])

    def test_identity_equality_extras_and_validation_precedence(self):
        result = run([
            {"op": "list", "id": "", "extra": {"x": [True], "y": 0}},
            {"extra": {"y": False, "x": [1]}, "id": "", "op": "list"},
            {"op": "list", "id": ""}, {"op": "put", "id": ""},
            {"op": "list", "id": None},
        ])
        self.assertEqual(result["events"], [{"ok": []}, {"ok": []},
                                           {"error": "id-conflict"}, {"error": "id-conflict"},
                                           {"error": "command"}])

    def test_failures_do_not_reserve_ids_and_runs_reset(self):
        commands = [{"op": "get", "key": "k", "id": "retry"}, put(id="retry")]
        first = run(commands)
        self.assertEqual(first["events"][0], {"error": "missing"})
        self.assertIn("ok", first["events"][1])
        self.assertEqual(run(commands), first)
        self.assertEqual(run([]), {"events": [], "state": [], "depth": 0})

    def test_python_equality_for_expect(self):
        with patch.object(core, "solve", return_value={"x": [True, False]}):
            result = run([put(), {"op": "expect", "key": "k", "value": {"x": [1, 0]}},
                          {"op": "expect", "key": "absent", "value": None}])
        self.assertEqual(result["events"][1:], [{"ok": True}, {"error": "expectation"}])

    def test_ownership_at_state_snapshot_and_event_boundaries(self):
        state, stack = {}, []
        source = {"nested": [1]}
        with patch.object(core, "solve", return_value=source):
            event = api._execute(put(), state, stack)
        source["nested"].append(2)
        event["ok"]["nested"].append(3)
        self.assertEqual(state, {"k": {"nested": [1]}})
        api._execute({"op": "begin"}, state, stack)
        state["k"]["nested"].append(4)
        self.assertEqual(stack, [{"k": {"nested": [1]}}])
        for command in [{"op": "get", "key": "k"}, {"op": "list"}]:
            value = api._execute(command, state, stack)["ok"]
            (value if isinstance(value, dict) else value[0][1])["nested"].append(5)
            self.assertEqual(state["k"]["nested"], [1, 4])
        api._execute({"op": "rollback"}, state, stack)
        self.assertEqual(state, {"k": {"nested": [1]}})


if __name__ == "__main__":
    unittest.main()
