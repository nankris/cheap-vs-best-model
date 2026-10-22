"""Exact account aggregation with final rounding to cents."""

from decimal import Decimal


def _balance_string(coefficient, exponent):
    """Round coefficient * 10**exponent using ROUND_HALF_EVEN."""
    magnitude = abs(coefficient)
    cents_exponent = exponent + 2
    if cents_exponent >= 0:
        cents = magnitude * 10 ** cents_exponent
    else:
        divisor = 10 ** -cents_exponent
        cents, remainder = divmod(magnitude, divisor)
        # At an exact tie, increment only when the retained digit is odd.
        if remainder * 2 > divisor or (
            remainder * 2 == divisor and cents % 2
        ):
            cents += 1
    sign = "-" if coefficient < 0 and cents else ""
    whole, fraction = divmod(cents, 100)
    # Decimal's integer conversion also handles balances beyond Python's
    # configurable limit on int-to-string conversions.
    return f"{sign}{Decimal(whole)}.{fraction:02d}"


def solve(rows):
    seen = set()
    balances = {}
    for account, amount, identifier in rows:
        if identifier in seen:
            continue
        seen.add(identifier)

        # Parsing a Decimal is exact. Do the arithmetic with integers so the
        # caller's decimal precision and rounding settings cannot affect sums.
        sign, digits, exponent = Decimal(amount).as_tuple()
        coefficient = 0
        for digit in digits:
            coefficient = coefficient * 10 + digit
        if sign:
            coefficient = -coefficient

        if account in balances:
            previous, previous_exponent = balances[account]
            common_exponent = min(previous_exponent, exponent)
            coefficient = (
                previous * 10 ** (previous_exponent - common_exponent)
                + coefficient * 10 ** (exponent - common_exponent)
            )
            exponent = common_exponent
        balances[account] = coefficient, exponent

    return [
        [account, _balance_string(*balances[account])]
        for account in sorted(balances)
    ]
