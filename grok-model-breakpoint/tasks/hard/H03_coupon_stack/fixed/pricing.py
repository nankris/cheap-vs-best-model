from decimal import Decimal, ROUND_HALF_EVEN

def apply_fraction(price_cents, fraction):
    value = Decimal(price_cents) * (Decimal(1) - Decimal(fraction))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
