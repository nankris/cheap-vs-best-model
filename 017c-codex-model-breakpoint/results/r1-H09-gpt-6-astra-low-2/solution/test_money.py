import json
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import localcontext
from itertools import permutations

from api import run
from core import Money
from render import present
from service import compute


class MoneyTests(unittest.TestCase):
    def test_frozen_value_and_addition(self):
        value = Money(123)
        self.assertTrue(is_dataclass(value))
        with self.assertRaises(FrozenInstanceError):
            value.cents = 456
        self.assertEqual(value + Money(-23), Money(100))
        self.assertEqual(value, Money(123))
        with self.assertRaises(TypeError):
            value + 1

    def test_exact_half_even_rounding(self):
        cases = {
            "0": 0, "1.005": 100, "1.015": 102,
            "-1.005": -100, "-1.015": -102,
            "0.005": 0, "-0.005": 0,
            "0.005000000000000000000000000001": 1,
            "0.004999999999999999999999999999": 0,
            "9.999": 1000, "-9.999": -1000, "1.25e2": 12500,
        }
        for source, cents in cases.items():
            with self.subTest(source=source):
                self.assertEqual(Money.parse(source), Money(cents))

    def test_round_each_row_and_empty_input(self):
        self.assertEqual(compute(["0.005", "0.005"]), Money(0))
        self.assertEqual(compute(["0.015", "0.015"]), Money(4))
        self.assertEqual(compute([]), Money(0))
        self.assertEqual(compute(iter(["0.1", "0.2"])), Money(30))

    def test_order_and_decimal_context_independence(self):
        rows = ["1000000000000000000000000000000.005",
                "-1000000000000000000000000000000", "0.015", "0.1"]
        with localcontext() as context:
            context.prec = 2
            for ordered in permutations(rows):
                self.assertEqual(compute(ordered), Money(12))
            large = Money.parse("123456789012345678901234567890.125")
            self.assertEqual(present(large), "123456789012345678901234567890.12")

    def test_render(self):
        for cents, expected in [(0, "0.00"), (1, "0.01"), (-1, "-0.01"),
                                (100, "1.00"), (-123, "-1.23")]:
            self.assertEqual(present(Money(cents)), expected)

    def test_json_api(self):
        self.assertEqual(run('["0.1", "0.2"]'), '"0.30"')
        self.assertEqual(json.loads(run('["1.005", "1.015"]')), "2.02")
        self.assertEqual(run("[]"), '"0.00"')
        self.assertEqual(run('["-0.015"]'), '"-0.02"')


if __name__ == "__main__":
    unittest.main()
