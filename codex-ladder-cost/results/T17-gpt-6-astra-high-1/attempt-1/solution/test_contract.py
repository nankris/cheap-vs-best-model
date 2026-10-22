import copy
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
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


def put(key, amount, **extra):
    return {"op": "put", "key": key, "input": [["a", amount, 1]], **extra}


class AlgorithmTests(unittest.TestCase):
    def test_rounding_deduplication_sorting_and_ownership(self):
        rows = [
            ["z", "0.005", 1], ["z", "0.005", 2],
            ["a", "99", 1], ["a", "2.345", 3],
            ["b", "2.355", 4], ["c", "-2.345", 5],
            ["d", "-2.355", 6], ["e", "-0.005", 7],
        ]
        before = copy.deepcopy(rows)
        self.assertEqual(core.solve(rows), [
            ["a", "2.34"], ["b", "2.36"], ["c", "-2.34"],
            ["d", "-2.36"], ["e", "0.00"], ["z", "0.01"],
        ])
        self.assertEqual(rows, before)
        self.assertEqual(core.solve([]), [])

    def test_exact_large_values_and_context_independence(self):
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(core.solve([
                ["a", "123456789012345678901234567890.005", 1],
                ["a", "0.005", 2],
            ]), [["a", "123456789012345678901234567890.01"]])
            self.assertEqual(core.solve([["a", "1e5000", 1]]),
                             [["a", "1" + "0" * 5000 + ".00"]])

    def test_randomized_against_decimal_reference(self):
        rng = random.Random(9123)
        with localcontext() as context:
            context.prec = 100
            for _ in range(100):
                rows = [[rng.choice(["", "a", "é", "中"]),
                         f"{rng.randrange(-1000000, 1000000)}e-{rng.randrange(7)}",
                         rng.randrange(40)] for _ in range(100)]
                totals, seen = {}, set()
                for account, amount, row_id in rows:
                    if row_id not in seen:
                        seen.add(row_id)
                        totals[account] = totals.get(account, Decimal(0)) + Decimal(amount)
                expected = []
                for account, total in sorted(totals.items()):
                    rounded = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                    expected.append([account, "0.00" if rounded == 0 else str(rounded)])
                self.assertEqual(core.solve(rows), expected)


class PipelineTests(unittest.TestCase):
    def test_shared_frozen_single_field_result(self):
        self.assertIs(service.Result, model.Result)
        self.assertIs(render.Result, model.Result)
        self.assertEqual([field.name for field in fields(model.Result)], ["value"])
        result = service.compute([])
        self.assertIsInstance(result, model.Result)
        self.assertEqual(result.value, [])
        with self.assertRaises(FrozenInstanceError):
            result.value = 2

    def test_all_json_shapes_pass_through_pipeline_and_journal(self):
        for value in [None, False, 0, 1.5, "é", [], [1, {"x": [True]}], {"a": 1}]:
            with self.subTest(value=value), patch.object(core, "solve", return_value=value):
                result = service.compute([])
                self.assertEqual(json.loads(render.present(result)), value)
                output = journal([put("", "0"), {"op": "get", "key": ""}])
                self.assertEqual(output["events"], [{"ok": value}, {"ok": value}])
                self.assertEqual(output["state"], [["", value]])


class JournalTests(unittest.TestCase):
    def test_nested_transactions(self):
        output = journal([
            {"op": "commit"}, {"op": "rollback"}, put("x", "1"),
            {"op": "begin"}, put("x", "2"), {"op": "begin"},
            {"op": "delete", "key": "x"}, {"op": "rollback"},
            {"op": "get", "key": "x"}, {"op": "commit"},
            {"op": "begin"}, put("x", "3"), {"op": "rollback"},
        ])
        self.assertEqual(output["events"], [
            {"error": "transaction"}, {"error": "transaction"},
            {"ok": [["a", "1.00"]]}, {"ok": 1}, {"ok": [["a", "2.00"]]},
            {"ok": 2}, {"ok": [["a", "2.00"]]}, {"ok": 1},
            {"ok": [["a", "2.00"]]}, {"ok": 0}, {"ok": 1},
            {"ok": [["a", "3.00"]]}, {"ok": 0},
        ])
        self.assertEqual(output["state"], [["x", [["a", "2.00"]]]])
        self.assertEqual(output["depth"], 0)

    def test_validation_is_atomic_and_extra_fields_ignored(self):
        malformed = [None, [], 1, "put", {}, {"op": []}, {"op": {}},
                     {"op": "unknown"}, {"op": "put", "key": "x"},
                     {"op": "expect", "key": "x"}]
        for op in ["put", "get", "delete", "expect"]:
            malformed.append({"op": op, "input": [], "value": None})
            malformed.extend({"op": op, "key": key, "input": [], "value": None}
                             for key in [None, False, 2, [], {}])
        malformed.extend({"op": "rollback", "id": value}
                         for value in [None, 1, False, [], {}])
        output = journal([put("x", "1"), {"op": "begin"}, *malformed,
                          {"op": "list", "key": 42, "extra": True}])
        self.assertEqual(output["events"][2:-1], [{"error": "command"}] * len(malformed))
        self.assertEqual(output["depth"], 1)
        self.assertEqual(output["events"][-1], {"ok": output["state"]})

    def test_replay_survives_rollback_and_does_not_restore_put(self):
        command = put("x", "1", id="")
        output = journal([{"op": "begin", "id": "b"}, command,
                          {"op": "rollback", "id": "r"}, command,
                          {"op": "begin", "id": "b"},
                          {"op": "rollback", "id": "r"},
                          {"op": "get", "key": "x"}])
        self.assertEqual(output["events"], [
            {"ok": 1}, {"ok": [["a", "1.00"]]}, {"ok": 0},
            {"ok": [["a", "1.00"]]}, {"ok": 1}, {"ok": 0}, {"error": "missing"},
        ])
        self.assertEqual(output["state"], [])
        self.assertEqual(output["depth"], 0)

    def test_identity_equality_extras_and_validation_precedence(self):
        output = journal([
            {"op": "begin", "id": "b", "extra": {"a": True, "b": [0]}},
            {"extra": {"b": [False], "a": 1}, "id": "b", "op": "begin"},
            {"op": "begin", "id": "b"}, {"op": "put", "id": "b"},
            {"op": "begin", "id": None},
        ])
        self.assertEqual(output["events"], [
            {"ok": 1}, {"ok": 1}, {"error": "id-conflict"},
            {"error": "id-conflict"}, {"error": "command"},
        ])
        self.assertEqual(output["depth"], 1)

    def test_failures_do_not_reserve_ids(self):
        output = journal([
            {"op": "get", "key": "x", "id": "a"}, put("x", "1", id="a"),
            {"op": "expect", "key": "x", "value": None, "id": "b"},
            {"op": "commit", "id": "b"}, {"op": "put", "id": "b"},
            {"op": "begin", "id": "b"},
        ])
        self.assertEqual(output["events"], [
            {"error": "missing"}, {"ok": [["a", "1.00"]]},
            {"error": "expectation"}, {"error": "transaction"},
            {"error": "command"}, {"ok": 1},
        ])

    def test_replayed_list_get_delete_commit_have_no_side_effects(self):
        output = journal([
            put("x", "1"), {"op": "list", "id": "l"},
            {"op": "get", "key": "x", "id": "g"},
            {"op": "delete", "key": "x", "id": "d"}, put("x", "2"),
            {"op": "delete", "key": "x", "id": "d"},
            {"op": "get", "key": "x", "id": "g"}, {"op": "list", "id": "l"},
            {"op": "begin"}, {"op": "commit", "id": "c"},
            {"op": "begin"}, {"op": "commit", "id": "c"},
        ])
        self.assertEqual(output["events"][1], output["events"][7])
        self.assertEqual(output["events"][2], output["events"][6])
        self.assertEqual(output["events"][3], output["events"][5])
        self.assertEqual(output["state"], [["x", [["a", "2.00"]]]])
        self.assertEqual(output["depth"], 1)

    def test_expect_python_equality_and_missing(self):
        with patch.object(core, "solve", return_value=[True, {"x": False}]):
            output = journal([
                put("", "0"), {"op": "expect", "key": "", "value": [1, {"x": 0}]},
                {"op": "expect", "key": "absent", "value": None},
            ])
        self.assertEqual(output["events"][1:], [{"ok": True}, {"error": "expectation"}])

    def test_unicode_sorting_and_run_isolation(self):
        keys = ["中", "é", "z", "", "😀"]
        output = journal([*(put(key, "0") for key in keys), {"op": "list"}])
        self.assertEqual([item[0] for item in output["state"]], sorted(keys))
        self.assertEqual(output["events"][-1], {"ok": output["state"]})
        journal([{"op": "begin", "id": "x"}, put("x", "1")])
        self.assertEqual(journal([]), {"events": [], "state": [], "depth": 0})
        self.assertEqual(journal([{"op": "list", "id": "x"}])["events"], [{"ok": []}])


if __name__ == "__main__":
    unittest.main()
