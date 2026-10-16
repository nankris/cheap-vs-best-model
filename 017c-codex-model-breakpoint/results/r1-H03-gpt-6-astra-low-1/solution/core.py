from decimal import Decimal
from fractions import Fraction


def solve(rows):
    seen = set()
    balances = {}
    for account, amount, row_id in rows:
        if row_id in seen:
            continue
        seen.add(row_id)
        # Fraction preserves every decimal digit without a context precision limit.
        balances[account] = balances.get(account, Fraction()) + Fraction(Decimal(amount))

    result = []
    for account in sorted(balances):
        # Fraction's round uses exact ties-to-even rounding.
        cents = round(balances[account] * 100)
        sign = "-" if cents < 0 else ""
        whole, remainder = divmod(abs(cents), 100)
        result.append([account, f"{sign}{whole}.{remainder:02d}"])
    return result
