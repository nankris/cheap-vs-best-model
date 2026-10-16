from decimal import Decimal

def fraction(coupon):
    percent = coupon["percent"]
    if not isinstance(percent, int) or isinstance(percent, bool) or not 0 <= percent <= 100:
        raise ValueError("percent")
    return Decimal(percent) / Decimal(100)
