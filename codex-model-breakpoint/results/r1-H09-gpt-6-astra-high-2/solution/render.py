from core import Money


def present(value: Money) -> str:
    whole, fractional = divmod(abs(value.cents), 100)
    sign = "-" if value.cents < 0 else ""
    return f"{sign}{whole}.{fractional:02d}"
