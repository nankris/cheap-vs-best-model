from core import Money


def present(value: Money) -> str:
    whole, fraction = divmod(abs(value.cents), 100)
    sign = "-" if value.cents < 0 else ""
    return f"{sign}{whole}.{fraction:02d}"
