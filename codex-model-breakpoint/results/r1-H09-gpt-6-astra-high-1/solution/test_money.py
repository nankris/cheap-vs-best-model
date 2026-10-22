import json
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import ROUND_UP, localcontext
from itertools import permutations

from api import run
from core import Money
from render import present
from service import compute


class MoneyTests(unittest.TestCase):
    def test_half_even_rounding(self):
        cases = {
            "0.005": 0,
            "0.015": 2,
            "0.025": 2,
            "1.225": 122,
            "1.235": 124,
            "-0.005": 0,
            "-0.015": -2,
            "-1.225": -122,
            "-1.235": -124,
            "2.6749": 267,
            "2.6751": 268,
            "-2.6749": -267,
            "-2.6751": -268,
            "1e-3": 0,
            "1.2345e2": 12345,
        }
        for value, cents in cases.items():
            with self.subTest(value=value):
                self.assertEqual(Money.parse(value), Money(cents))

    def test_immutable_dataclass_and_addition(self):
        value = Money(123)
        self.assertTrue(is_dataclass(value))
        with self.assertRaises(FrozenInstanceError):
            value.cents = 0
        self.assertEqual(value + Money(-24), Money(99))
        self.assertEqual(value, Money(123))
        with self.assertRaises(TypeError):
            value + 1

    def test_round_each_row(self):
        self.assertEqual(compute(["0.005", "0.005"]), Money(0))
        self.assertEqual(compute(["0.015", "0.015"]), Money(4))
        self.assertEqual(compute([]), Money(0))
        self.assertEqual(compute(iter(["1.00", "2.00"])), Money(300))

    def test_order_independence_and_exact_large_values(self):
        rows = ["1000000000000000000000000000000.01",
                "-1000000000000000000000000000000", "0.015", "-0.005"]
        for ordering in permutations(rows):
            self.assertEqual(compute(ordering), Money(3))

    def test_decimal_context_does_not_change_results(self):
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_UP
            value = Money.parse("123456789012345678901234567890.125")
            self.assertEqual(value.cents, 12345678901234567890123456789012)
            self.assertEqual(present(value), "123456789012345678901234567890.12")
            self.assertEqual(Money.parse("0.005"), Money(0))

    def test_formatting(self):
        for cents, expected in [(0, "0.00"), (1, "0.01"), (-1, "-0.01"),
                                (110, "1.10"), (-12345, "-123.45")]:
            with self.subTest(cents=cents):
                self.assertEqual(present(Money(cents)), expected)

    def test_json_api(self):
        self.assertEqual(run('["1.225", "2.235", "-0.01"]'), '"3.45"')
        self.assertEqual(run('[]'), '"0.00"')
        self.assertEqual(json.loads(run('["-0.015"]')), "-0.02")
        with self.assertRaises(json.JSONDecodeError):
            run("1.00,2.00")


if __name__ == "__main__":
    unittest.main()
