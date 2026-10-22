from core import Money


def present(value):
    if not isinstance(value, Money):
        raise TypeError("value must be Money")
    sign = "-" if value.cents < 0 else ""
    cents = abs(value.cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"
