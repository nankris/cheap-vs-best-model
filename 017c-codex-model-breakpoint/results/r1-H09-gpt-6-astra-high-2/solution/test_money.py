import itertools
import json
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Inexact, ROUND_UP, localcontext

from api import run
from core import Money
from render import present
from service import compute


class MoneyTests(unittest.TestCase):
    def test_frozen_dataclass_and_addition(self):
        self.assertTrue(is_dataclass(Money))
        value = Money(12)
        with self.assertRaises(FrozenInstanceError):
            value.cents = 13
        self.assertEqual(value + Money(-5), Money(7))
        self.assertEqual(value, Money(12))
        self.assertEqual(hash(value), hash(Money(12)))
        with self.assertRaises(TypeError):
            value + 5

    def test_exact_half_even_rounding(self):
        cases = {
            "0.005": 0,
            "0.015": 2,
            "1.225": 122,
            "1.235": 124,
            "-1.225": -122,
            "-1.235": -124,
            "9.999": 1000,
            "1.234999999999999999999999999999999": 123,
            "1.235000000000000000000000000000001": 124,
            "1e-100": 0,
            "1e3": 100000,
        }
        for source, cents in cases.items():
            with self.subTest(source=source):
                self.assertEqual(Money.parse(source), Money(cents))

    def test_large_values_and_decimal_context_independence(self):
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_UP
            context.traps[Inexact] = True
            self.assertEqual(Money.parse("1.225"), Money(122))
            self.assertEqual(
                Money.parse("123456789012345678901234567890.125"),
                Money(12345678901234567890123456789012),
            )

    def test_nonfinite_values_are_rejected(self):
        for source in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                Money.parse(source)

    def test_compute_rounds_each_row(self):
        self.assertEqual(compute(["0.005", "0.005"]), Money(0))
        self.assertEqual(compute(["0.015", "0.015"]), Money(4))
        self.assertEqual(compute([]), Money(0))
        self.assertEqual(compute(iter(["1.25", "2.50"])), Money(375))

    def test_input_order_independence(self):
        rows = ["100000000000000000000.00", "0.015", "-100000000000000000000.00", "0.005"]
        for permutation in itertools.permutations(rows):
            self.assertEqual(compute(permutation), Money(2))

    def test_render_two_decimal_places(self):
        for cents, expected in ((0, "0.00"), (1, "0.01"), (-1, "-0.01"),
                                (100, "1.00"), (-123, "-1.23"),
                                (123456789012345678901, "1234567890123456789.01")):
            with self.subTest(cents=cents):
                self.assertEqual(present(Money(cents)), expected)

    def test_json_api(self):
        self.assertEqual(run('["1.225", "2.345"]'), '"3.56"')
        self.assertEqual(run('[]'), '"0.00"')
        self.assertEqual(json.loads(run('["-0.015"]')), "-0.02")
        self.assertEqual(run('["0.005", "0.005"]'), '"0.00"')
        with self.assertRaises(json.JSONDecodeError):
            run("1.25,2.50")


if __name__ == "__main__":
    unittest.main()
