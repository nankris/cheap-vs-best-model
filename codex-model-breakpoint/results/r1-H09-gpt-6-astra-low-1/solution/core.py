from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    cents: int

    @classmethod
    def parse(cls, decimal_string: str) -> "Money":
        # Integer arithmetic keeps rounding exact regardless of Decimal context.
        numerator, denominator = Decimal(decimal_string).as_integer_ratio()
        cents, remainder = divmod(abs(numerator) * 100, denominator)
        if remainder * 2 > denominator or (
            remainder * 2 == denominator and cents % 2
        ):
            cents += 1
        return cls(-cents if numerator < 0 else cents)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)
