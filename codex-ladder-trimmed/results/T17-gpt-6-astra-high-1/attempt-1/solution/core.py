from decimal import Decimal
from fractions import Fraction


def solve(rows):
    balances = {}
    seen = set()
    seen_unhashable = []
    for account, amount, row_id in rows:
        try:
            if row_id in seen:
                continue
            seen.add(row_id)
        except TypeError:
            if row_id in seen_unhashable:
                continue
            seen_unhashable.append(row_id)

        # Fractions preserve every decimal digit, independently of the active
        # decimal context's precision and rounding mode.
        balances[account] = balances.get(account, Fraction(0)) + Fraction(Decimal(amount))

    result = []
    for account in sorted(balances):
        balance = balances[account]
        cents, remainder = divmod(abs(balance.numerator) * 100, balance.denominator)
        # ROUND_HALF_EVEN: ties advance only when the retained cent is odd.
        twice_remainder = remainder * 2
        if twice_remainder > balance.denominator or (
            twice_remainder == balance.denominator and cents % 2
        ):
            cents += 1
        sign = "-" if balance < 0 and cents else ""
        result.append([account, f"{sign}{cents // 100}.{cents % 100:02d}"])
    return result
