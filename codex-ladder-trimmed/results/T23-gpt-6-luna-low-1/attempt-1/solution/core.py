from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string):
        value = Decimal(decimal_string)
        # quantize needs enough precision for every input digit and the two
        # fractional places, including very large valid decimal strings.
        with localcontext() as context:
            context.prec = max(28, len(value.as_tuple().digits) + abs(value.as_tuple().exponent) + 4)
            amount = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        parts = amount.as_tuple()
        cents = int("".join(str(digit) for digit in parts.digits) or "0")
        return cls(-cents if parts.sign else cents)

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)


def solve(rows):
    total = sum(Money.parse(row).cents for row in rows)
    sign = "-" if total < 0 else ""
    absolute = abs(total)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"
