from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string: str) -> "Money":
        if not isinstance(decimal_string, str):
            raise TypeError("decimal_string must be a string")
        try:
            amount = Decimal(decimal_string)
        except InvalidOperation as exc:
            raise ValueError(f"invalid decimal amount: {decimal_string!r}") from exc
        cents = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
        return cls(int(cents))

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)
