from decimal import Decimal, ROUND_HALF_EVEN
from coupon import fraction as coupon_fraction

def total(price_cents, coupons):
    if not isinstance(price_cents, int) or isinstance(price_cents, bool):
        raise ValueError("price")
    value = Decimal(price_cents)
    for coupon in coupons:
        frac = coupon_fraction(coupon)
        value = value * (Decimal(1) - frac)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
