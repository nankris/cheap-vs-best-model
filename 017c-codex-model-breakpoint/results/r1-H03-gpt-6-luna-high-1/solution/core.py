from decimal import Decimal, ROUND_HALF_EVEN, localcontext


def _decimal_from_units(units, exponent):
    """Build a Decimal without applying the active context."""
    sign = 1 if units < 0 else 0
    digits = tuple(int(char) for char in str(abs(units)))
    return Decimal((sign, digits, exponent))


def solve(rows):
    """Return sorted account balances rounded to cents, ties to even."""
    seen_ids = set()
    totals = {}

    for account, amount_text, row_id in rows:
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)

        amount = Decimal(amount_text)
        sign, digits, exponent = amount.as_tuple()
        units = int("".join(str(digit) for digit in digits) or "0")
        if sign:
            units = -units

        if account not in totals:
            totals[account] = (units, exponent)
            continue

        old_units, old_exponent = totals[account]
        common_exponent = min(old_exponent, exponent)
        old_units *= 10 ** (old_exponent - common_exponent)
        units *= 10 ** (exponent - common_exponent)
        totals[account] = (old_units + units, common_exponent)

    result = []
    for account in sorted(totals):
        units, exponent = totals[account]
        exact_total = _decimal_from_units(units, exponent)
        # quantize needs enough precision for every integer digit plus cents.
        integer_digits = max(1, exact_total.adjusted() + 1) if exact_total else 1
        precision = max(28, integer_digits + 3, len(exact_total.as_tuple().digits) + 3)
        with localcontext() as context:
            context.prec = precision
            rounded = exact_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        if rounded.is_zero():
            rounded = Decimal("0.00")
        result.append([account, format(rounded, ".2f")])

    return result
