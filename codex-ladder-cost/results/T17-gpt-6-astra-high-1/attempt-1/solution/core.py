"""Exact account balances, with global first-wins row deduplication."""

from decimal import Decimal


def solve(rows):
    balances = {}
    seen = set()
    seen_containers = []
    for account, amount, row_id in rows:
        # JSON container ids are also comparable by ordinary Python equality.
        if isinstance(row_id, (list, dict)):
            if row_id in seen_containers:
                continue
            seen_containers.append(row_id)
        else:
            if row_id in seen:
                continue
            seen.add(row_id)

        parts = Decimal(amount).as_tuple()
        coefficient = 0
        for digit in parts.digits:
            coefficient = coefficient * 10 + digit
        if parts.sign:
            coefficient = -coefficient
        exponent = parts.exponent
        if account in balances:
            previous, previous_exponent = balances[account]
            common_exponent = min(exponent, previous_exponent)
            coefficient = (
                previous * 10 ** (previous_exponent - common_exponent)
                + coefficient * 10 ** (exponent - common_exponent)
            )
            exponent = common_exponent
        balances[account] = coefficient, exponent

    result = []
    for account in sorted(balances):
        coefficient, exponent = balances[account]
        # Convert the exact total to cents, rounding ties to an even integer.
        if exponent >= -2:
            cents = abs(coefficient) * 10 ** (exponent + 2)
        else:
            divisor = 10 ** (-exponent - 2)
            cents, remainder = divmod(abs(coefficient), divisor)
            if remainder * 2 > divisor or (
                remainder * 2 == divisor and cents % 2
            ):
                cents += 1
        sign = "-" if coefficient < 0 and cents else ""
        whole, fraction = divmod(cents, 100)
        # Decimal's integer conversion also handles balances beyond Python's
        # configurable limit for converting very large integers to strings.
        result.append([account, f"{sign}{Decimal(whole)}.{fraction:02d}"])
    return result
