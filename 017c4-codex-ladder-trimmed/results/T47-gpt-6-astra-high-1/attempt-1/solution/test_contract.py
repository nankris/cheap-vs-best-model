import copy
import json
import random
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from unittest.mock import patch

import api
import core
import model
import render
import service


class ContractTests(unittest.TestCase):
    def test_global_first_id_wins_and_accounts_sorted(self):
        rows = [
            ["z", "1.005", "one"],
            ["a", "100", "one"],
            ["z", "0.005", "two"],
            ["b", "-0.005", "three"],
            ["a", "2.345", "four"],
        ]
        original = copy.deepcopy(rows)
        expected = [["a", "2.34"], ["b", "0.00"], ["z", "1.01"]]
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(core.solve(rows), expected)
        self.assertEqual(rows, original)

    def test_rounding_and_decimal_notation(self):
        amounts = ["1.005", "1.015", "-1.005", "-1.015", "-0.000", "12e2", ".009"]
        expected = ["1.00", "1.02", "-1.00", "-1.02", "0.00", "1200.00", "0.01"]
        for amount, balance in zip(amounts, expected):
            with self.subTest(amount=amount):
                self.assertEqual(core.solve([["a", amount, 1]]), [["a", balance]])

    def test_precision_and_cancellation(self):
        rows = [
            ["a", "123456789012345678901234567890.005", 1],
            ["a", "0.005", 2],
            ["b", "1e80", 3],
            ["b", "0.015", 4],
            ["b", "-1e80", 5],
        ]
        with localcontext() as context:
            context.prec = 2
            context.rounding = "ROUND_DOWN"
            self.assertEqual(core.solve(rows), [
                ["a", "123456789012345678901234567890.01"],
                ["b", "0.02"],
            ])

    def test_very_large_balance(self):
        self.assertEqual(core.solve([["a", "1e5000", 1]]),
                         [["a", "1" + "0" * 5000 + ".00"]])

    def test_public_result_service_and_renderer(self):
        result = model.Result([["a", "1.00"]])
        self.assertTrue(is_dataclass(result))
        with self.assertRaises(FrozenInstanceError):
            result.value = []
        self.assertEqual(render.present(result), json.dumps(result.value))
        rows = [["a", "1", 1]]
        with patch.object(core, "solve", return_value=[["stub", "2.00"]]) as solve:
            self.assertEqual(service.compute(rows), model.Result([["stub", "2.00"]]))
            solve.assert_called_once_with(rows)

    def test_api_batch_order_and_independent_calls(self):
        inputs = [[], [["a", "1", 1]], [["b", "2", 1]]]
        expected = [[], [["a", "1.00"]], [["b", "2.00"]]]
        payload = json.dumps(inputs)
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(json.loads(api.run(payload)), expected)
        self.assertEqual(api.run("[]"), "[]")
        with patch.object(service, "compute", wraps=service.compute) as compute:
            with patch.object(render, "present", wraps=render.present) as present:
                self.assertEqual(json.loads(api.run(payload)), expected)
                self.assertEqual([call.args[0] for call in compute.call_args_list], inputs)
                self.assertEqual(present.call_count, len(inputs))

    def test_randomized_against_high_precision_decimal(self):
        rng = random.Random(42)
        with localcontext() as context:
            context.prec = 200
            for _ in range(100):
                rows = []
                totals = {}
                seen = set()
                for _ in range(50):
                    account = rng.choice(["a", "b", "c"])
                    amount = str(rng.randrange(-10**30, 10**30)) + "e" + str(rng.randrange(-35, 10))
                    transaction_id = rng.randrange(35)
                    rows.append([account, amount, transaction_id])
                    if transaction_id not in seen:
                        seen.add(transaction_id)
                        totals[account] = totals.get(account, Decimal(0)) + Decimal(amount)
                expected = []
                for account, total in sorted(totals.items()):
                    rounded = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                    expected.append([account, "0.00" if rounded == 0 else format(rounded, "f")])
                self.assertEqual(core.solve(rows), expected)


if __name__ == "__main__":
    unittest.main()
