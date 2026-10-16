"""Exact account balances, with duplicate transaction IDs ignored."""

from decimal import Decimal


def _balance_string(coefficient, exponent):
    """Round an integer times a power of ten to cents, ties to even."""
    magnitude = abs(coefficient)
    if exponent >= -2:
        cents = magnitude * 10 ** (exponent + 2)
    else:
        divisor = 10 ** (-2 - exponent)
        cents, remainder = divmod(magnitude, divisor)
        if remainder * 2 > divisor or (remainder * 2 == divisor and cents % 2):
            cents += 1

    # Decimal's integer conversion and fixed formatting are exact and do not
    # depend on context precision (or the integer-to-string digit limit).
    digits = format(Decimal(cents), "f").zfill(3)
    sign = "-" if coefficient < 0 and cents else ""
    return sign + digits[:-2] + "." + digits[-2:]


def solve(rows):
    seen = set()
    totals = {}
    for account, amount, transaction_id in rows:
        if transaction_id in seen:
            continue
        seen.add(transaction_id)

        parts = Decimal(amount).as_tuple()
        coefficient = 0
        for digit in parts.digits:
            coefficient = coefficient * 10 + digit
        if parts.sign:
            coefficient = -coefficient
        exponent = parts.exponent

        if account in totals:
            previous, previous_exponent = totals[account]
            common_exponent = min(previous_exponent, exponent)
            coefficient = (
                previous * 10 ** (previous_exponent - common_exponent)
                + coefficient * 10 ** (exponent - common_exponent)
            )
            exponent = common_exponent
        totals[account] = (coefficient, exponent)

    return [
        [account, _balance_string(*totals[account])]
        for account in sorted(totals)
    ]
