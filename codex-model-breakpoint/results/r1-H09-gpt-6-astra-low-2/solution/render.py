from core import Money


def present(value: Money) -> str:
    dollars, cents = divmod(abs(value.cents), 100)
    sign = "-" if value.cents < 0 else ""
    return f"{sign}{dollars}.{cents:02d}"
