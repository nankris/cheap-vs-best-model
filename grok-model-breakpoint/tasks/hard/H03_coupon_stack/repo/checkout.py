from coupon import fraction as coupon_fraction
from pricing import apply_fraction

def total(price_cents, coupons):
    off = 0
    for coupon in coupons:
        off += coupon_fraction(coupon)
    return apply_fraction(price_cents, off)
