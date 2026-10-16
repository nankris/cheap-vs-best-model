from core import Money


def present(value: Money) -> str:
    sign = "-" if value.cents < 0 else ""
    dollars, cents = divmod(abs(value.cents), 100)
    return f"{sign}{dollars}.{cents:02d}"
