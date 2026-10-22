from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string: str) -> "Money":
        # Decimal construction and integer arithmetic are exact regardless of
        # the caller's decimal precision or rounding context.
        numerator, denominator = Decimal(decimal_string).as_integer_ratio()
        cents, remainder = divmod(numerator * 100, denominator)
        if remainder * 2 > denominator or (
            remainder * 2 == denominator and cents % 2
        ):
            cents += 1
        return cls(cents)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)


def solve(rows: Iterable[str]) -> Money:
    return sum((Money.parse(row) for row in rows), Money(0))
