import itertools
import json
import unittest
from dataclasses import FrozenInstanceError
from decimal import localcontext

from api import run
from core import Money
from render import present
from service import compute


class MoneyTests(unittest.TestCase):
    def test_half_even_rounding(self):
        for value, cents in [
            ("1.005", 100), ("1.015", 102), ("1.025", 102),
            ("-1.005", -100), ("-1.015", -102), ("-1.025", -102),
            ("0.005", 0), ("-0.005", 0), ("0.00501", 1),
            ("0.00499", 0), ("1e-2", 1),
        ]:
            with self.subTest(value=value):
                self.assertEqual(Money.parse(value), Money(cents))

    def test_immutable_addition(self):
        left = Money(12)
        self.assertEqual(left + Money(-5), Money(7))
        self.assertEqual(left, Money(12))
        with self.assertRaises(FrozenInstanceError):
            left.cents = 0
        with self.assertRaises(TypeError):
            left + 1

    def test_exact_under_small_decimal_context(self):
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(
                Money.parse("123456789012345678901234567890.015"),
                Money(12345678901234567890123456789002),
            )

    def test_each_row_is_rounded(self):
        self.assertEqual(compute(["0.005", "0.005"]), Money(0))
        self.assertEqual(compute(["0.015", "0.015"]), Money(4))
        self.assertEqual(compute([]), Money(0))

    def test_order_independent(self):
        rows = ["100000000000000000000.01", "-100000000000000000000", "0.015"]
        for ordering in itertools.permutations(rows):
            self.assertEqual(compute(ordering), Money(3))

    def test_render(self):
        for cents, expected in [(0, "0.00"), (1, "0.01"), (-1, "-0.01"),
                                (120, "1.20"), (-12345, "-123.45")]:
            self.assertEqual(present(Money(cents)), expected)

    def test_json_api(self):
        self.assertEqual(run(json.dumps(["1.015", "2.00", "-0.005"])), '"3.02"')
        self.assertEqual(json.loads(run("[]")), "0.00")
        self.assertEqual(json.loads(run('["1e2", "-0.01"]')), "99.99")


if __name__ == "__main__":
    unittest.main()
