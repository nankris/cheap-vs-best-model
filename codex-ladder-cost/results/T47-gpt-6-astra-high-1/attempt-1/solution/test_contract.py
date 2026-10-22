import copy
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_UP, localcontext
import json
import random
import unittest
from unittest.mock import patch

import api
import core
from model import Result
import render
import service


class ContractTests(unittest.TestCase):
    def test_model(self):
        result = Result([["a", "1.00"]])
        self.assertTrue(is_dataclass(result))
        self.assertEqual(result.value, [["a", "1.00"]])
        with self.assertRaises(FrozenInstanceError):
            result.value = []

    def test_service(self):
        rows = [["a", "1", "id"]]
        value = [["a", "1.00"]]
        with patch.object(core, "solve", return_value=value) as solve:
            result = service.compute(rows)
        solve.assert_called_once_with(rows)
        self.assertIsInstance(result, Result)
        self.assertIs(result.value, value)

    def test_render(self):
        value = [["quoted\"\\\n café", "1.00"]]
        self.assertEqual(render.present(Result(value)), json.dumps(value))

    def test_empty_and_batch(self):
        self.assertEqual(core.solve([]), [])
        self.assertEqual(json.loads(api.run("[]")), [])
        inputs = [[], [["b", "1.005", "same"]],
                  [["a", "2.015", "same"]], []]
        expected = [[], [["b", "1.00"]], [["a", "2.02"]], []]
        self.assertEqual(json.loads(api.run(json.dumps(inputs))), expected)
        self.assertEqual(json.loads(api.run(json.dumps(inputs))), expected)

    def test_pipeline_for_every_input(self):
        inputs = [[], [["a", "1", "id"]]]
        results = [Result([1]), Result([2])]
        with patch.object(service, "compute", side_effect=results) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(json.dumps(inputs))), [[1], [2]])
        self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
        self.assertEqual([call.args[0] for call in present.call_args_list], results)

    def test_global_deduplication_and_sort(self):
        rows = [["z", "1.20", "shared"], ["a", "100", "shared"],
                ["z", "1000", "shared"], ["a", "2.3", "unique"],
                ["only-duplicate", "99", "shared"]]
        self.assertEqual(core.solve(rows), [["a", "2.30"], ["z", "1.20"]])

    def test_rounding_and_negative_zero(self):
        cases = {"1.005": "1.00", "1.015": "1.02", "1.025": "1.02",
                 "-1.005": "-1.00", "-1.015": "-1.02", "9.995": "10.00",
                 "-0.005": "0.00", "-0.0001": "0.00", "-0": "0.00",
                 "1.005000001": "1.01", "1.004999999": "1.00",
                 "1e3": "1000.00", "5e-3": "0.00"}
        for amount, expected in cases.items():
            with self.subTest(amount=amount):
                self.assertEqual(core.solve([["a", amount, 1]]), [["a", expected]])

    def test_round_only_at_end(self):
        self.assertEqual(core.solve([["a", ".005", 1], ["a", ".005", 2]]),
                         [["a", "0.01"]])

    def test_exact_sum_and_context_independence(self):
        rows = [["a", "123456789012345678901234567890.005", 1],
                ["a", ".005", 2], ["b", "1e40", 3],
                ["b", "0.015", 4], ["b", "-1e40", 5]]
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.rounding = ROUND_UP
            self.assertEqual(core.solve(rows),
                             [["a", "123456789012345678901234567890.01"],
                              ["b", "0.02"]])
            self.assertEqual(ctx.prec, 2)
            self.assertEqual(ctx.rounding, ROUND_UP)

    def test_large_balance(self):
        amount = "1" + "0" * 5000
        self.assertEqual(core.solve([["a", amount, 1]]), [["a", amount + ".00"]])

    def test_no_mutation_or_persistent_state(self):
        rows = [["b", "1.50", 1], ["a", "-1.50", 2]]
        original = copy.deepcopy(rows)
        result = service.compute(rows)
        self.assertEqual(rows, original)
        result.value[0][1] = "changed"
        self.assertEqual(rows, original)
        self.assertEqual(core.solve(rows), [["a", "-1.50"], ["b", "1.50"]])

    def test_randomized_decimal_reference(self):
        rng = random.Random(734)
        with localcontext() as ctx:
            ctx.prec = 100
            for _ in range(100):
                rows = [[rng.choice(["a", "b", "c"]),
                         f"{rng.randint(-100000, 100000)}e{rng.randint(-8, 8)}",
                         rng.randrange(40)] for _ in range(100)]
                totals, seen = {}, set()
                for account, amount, identifier in rows:
                    if identifier not in seen:
                        seen.add(identifier)
                        totals[account] = totals.get(account, Decimal(0)) + Decimal(amount)
                expected = []
                for account, value in sorted(totals.items()):
                    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                    expected.append([account, "0.00" if rounded == 0 else str(rounded)])
                self.assertEqual(core.solve(rows), expected)


if __name__ == "__main__":
    unittest.main()
