from collections import defaultdict
from decimal import Decimal


def solve(rows):
    """Aggregate exact decimal amounts, retaining the first occurrence of each id."""
    seen = set()
    balances = defaultdict(Decimal)

    for row in rows:
        account, amount, identifier = row
        if identifier in seen:
            continue
        seen.add(identifier)
        balances[account] += Decimal(amount)

    return sorted(balances.items())
