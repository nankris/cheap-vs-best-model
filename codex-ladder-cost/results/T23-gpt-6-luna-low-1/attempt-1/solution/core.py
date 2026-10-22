from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string: str) -> "Money":
        value = Decimal(decimal_string)
        # quantize uses the active Decimal precision; size it to the input so
        # valid large values are still rounded exactly to cents.
        with localcontext() as context:
            context.prec = max(context.prec, len(value.as_tuple().digits) + abs(value.as_tuple().exponent) + 3)
            amount = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        return cls(int(amount * 100))

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)


def solve(rows):
    cents = sum(Money.parse(row).cents for row in rows)
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"
