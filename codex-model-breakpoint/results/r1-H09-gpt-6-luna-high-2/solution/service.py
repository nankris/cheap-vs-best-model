from core import Money


def compute(rows):
    total = Money(0)
    for row in rows:
        total = total + Money.parse(row)
    return total
