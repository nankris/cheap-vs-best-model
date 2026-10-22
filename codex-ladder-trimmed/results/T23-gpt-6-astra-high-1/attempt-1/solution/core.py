"""Exact, per-row half-even rounding and summation of decimal money."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string):
        value = Decimal(decimal_string)
        sign, digits, exponent = value.as_tuple()
        # Shift without context-dependent multiplication. Integral rounding
        # preserves every integer digit regardless of the context precision.
        cents = Decimal((sign, digits, exponent + 2))
        return cls(int(cents.to_integral_value(rounding=ROUND_HALF_EVEN)))

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)


def solve(rows):
    total = Money(0)
    for row in rows:
        total = total + Money.parse(row)
    whole, fraction = divmod(abs(total.cents), 100)
    sign = "-" if total.cents < 0 else ""
    return f"{sign}{whole}.{fraction:02d}"
