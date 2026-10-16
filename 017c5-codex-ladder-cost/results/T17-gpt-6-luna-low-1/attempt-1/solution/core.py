from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN


def solve(rows):
    seen_ids = set()
    balances = defaultdict(Decimal)
    for account, amount_text, row_id in rows:
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)
        balances[account] += Decimal(amount_text)

    quantum = Decimal("0.01")
    result = []
    for account in sorted(balances):
        rounded = balances[account].quantize(quantum, rounding=ROUND_HALF_EVEN)
        if rounded == 0:
            rounded = abs(rounded)
        result.append([account, format(rounded, ".2f")])
    return result
