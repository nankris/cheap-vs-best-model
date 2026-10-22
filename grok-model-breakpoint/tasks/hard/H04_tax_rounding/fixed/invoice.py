from decimal import Decimal
from tax import line_tax

def total_tax(amounts, rate):
    total = sum((Decimal(line_tax(amount, rate)) for amount in amounts), Decimal("0"))
    return format(total.quantize(Decimal("0.01")), "f")
