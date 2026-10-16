from decimal import Decimal, ROUND_HALF_EVEN
from money import as_decimal

def line_tax(amount, rate):
    value = as_decimal(amount) * as_decimal(rate)
    cents = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return format(cents, "f")
