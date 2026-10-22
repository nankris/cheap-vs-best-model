from decimal import Decimal

def as_decimal(text):
    try:
        return Decimal(text)
    except Exception as exc:
        raise ValueError(text) from exc
