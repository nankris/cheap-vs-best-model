from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN


def solve(rows):
    """Aggregate unique transaction ids into rounded per-account balances."""
    seen_ids = set()
    totals = defaultdict(Decimal)

    for account, amount_text, transaction_id in rows:
        if transaction_id in seen_ids:
            continue
        seen_ids.add(transaction_id)
        totals[account] += Decimal(amount_text)

    cent = Decimal("0.01")
    result = []
    for account in sorted(totals):
        balance = totals[account].quantize(cent, rounding=ROUND_HALF_EVEN)
        if balance == 0:
            balance = Decimal("0.00")
        result.append([account, format(balance, ".2f")])
    return result
