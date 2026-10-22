"""Exact, individually rounded decimal money arithmetic."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string):
        sign, digits, exponent = Decimal(decimal_string).as_tuple()
        coefficient = 0
        for digit in digits:
            coefficient = coefficient * 10 + digit

        # Work with the exact decimal coefficient so the caller's Decimal
        # context cannot round large amounts before the cents rounding step.
        shift = exponent + 2
        if coefficient == 0 or shift < -len(digits):
            cents = 0
        elif shift >= 0:
            cents = coefficient * 10 ** shift
        else:
            divisor = 10 ** (-shift)
            cents, remainder = divmod(coefficient, divisor)
            if remainder * 2 > divisor or (
                remainder * 2 == divisor and cents % 2
            ):
                cents += 1
        return cls(-cents if sign else cents)

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)


def solve(rows):
    total = Money(0)
    for row in rows:
        total = total + Money.parse(row)
    magnitude = abs(total.cents)
    sign = "-" if total.cents < 0 else ""
    # Decimal formatting also handles amounts beyond Python's int-to-string
    # digit limit, without changing any process-wide settings.
    dollars = format(Decimal(magnitude // 100), "f")
    return f"{sign}{dollars}.{magnitude % 100:02d}"
