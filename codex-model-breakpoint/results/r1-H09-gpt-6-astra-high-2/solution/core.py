from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from typing import Iterable


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string: str) -> "Money":
        amount = Decimal(decimal_string)
        if not amount.is_finite():
            raise ValueError("Money must be finite")

        # Allow all integer digits and two fractional digits, regardless of the
        # caller's decimal precision. Reserve room for a rounding carry too.
        precision = max(1, len(amount.as_tuple().digits), amount.adjusted() + 4)
        with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
            rounded = amount.quantize(Decimal("0.01"))
            return cls(int(rounded * 100))

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)


def solve(rows: Iterable[str]) -> Money:
    return sum((Money.parse(row) for row in rows), Money(0))
