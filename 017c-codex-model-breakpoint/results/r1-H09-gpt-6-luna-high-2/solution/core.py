from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string: str) -> "Money":
        amount = Decimal(decimal_string)
        with localcontext() as context:
            context.prec = max(context.prec, amount.adjusted() + 3, 2)
            rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        parts = rounded.as_tuple()
        cents = int("".join(str(digit) for digit in parts.digits) or "0")
        return cls(-cents if parts.sign else cents)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)
