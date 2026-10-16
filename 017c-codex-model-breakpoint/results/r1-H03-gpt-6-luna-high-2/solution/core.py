"""Exact aggregation and final currency rounding."""

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import json


def solve(rows):
    """Aggregate ``[account, amount, id]`` rows and return sorted balances."""
    seen = set()
    amount_values = {}

    for account, amount, row_id in rows:
        # JSON serialization handles both ordinary scalar ids and composite
        # JSON ids without making the API depend on ids being hashable.
        id_key = json.dumps(row_id, sort_keys=True, separators=(",", ":"))
        if id_key in seen:
            continue
        seen.add(id_key)

        value = Decimal(amount)
        amount_values.setdefault(account, []).append(value)

    result = []
    for account in sorted(amount_values):
        values = amount_values[account]
        # Decimal arithmetic is exact only when the context has enough
        # precision for the full exponent span and the number of additions.
        if values:
            highest_place = max((v.adjusted() for v in values if v), default=0)
            lowest_place = min(v.as_tuple().exponent for v in values)
            precision = max(28, highest_place - lowest_place + len(str(len(values))) + 4)
        else:
            precision = 28
        with localcontext() as ctx:
            ctx.prec = precision
            balance = sum(values, Decimal(0)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
        if balance == 0:
            balance = Decimal("0.00")
        result.append([account, format(balance, ".2f")])
    return result
