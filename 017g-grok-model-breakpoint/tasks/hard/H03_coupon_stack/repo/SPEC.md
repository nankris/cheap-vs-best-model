# Coupon checkout

Prices are integer cents. A coupon is a dict `{"percent": N}` where N is an integer from 0 through 100 meaning N percent off. Anything else raises `ValueError`.

- `coupon.fraction(coupon)` returns the fraction off as a `decimal.Decimal`, so 15 becomes `Decimal("0.15")`.
- `pricing.apply_fraction(price_cents, fraction)` multiplies the price by `(1 - fraction)`.
- `checkout.total(price_cents, coupons)` applies every coupon, multiplicatively, in order. Round half-even to the nearest cent only once, at the end. No coupons returns the price unchanged. A 100 percent coupon returns 0.

Two 10 percent coupons on 8000 cents is 6480, not 6400. One 15 percent coupon on 8000 cents is 6800. The visible test only checks the single 15 percent coupon.
