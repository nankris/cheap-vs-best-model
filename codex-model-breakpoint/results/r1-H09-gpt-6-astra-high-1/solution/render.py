from core import Money


def present(value: Money) -> str:
    units, cents = divmod(abs(value.cents), 100)
    sign = "-" if value.cents < 0 else ""
    return f"{sign}{units}.{cents:02d}"
