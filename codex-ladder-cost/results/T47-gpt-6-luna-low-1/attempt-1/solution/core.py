from decimal import Decimal, ROUND_HALF_EVEN


def solve(rows):
    """Aggregate first-seen transaction ids by account and round at the end."""
    seen_ids = set()
    balances = {}

    for account, amount_text, transaction_id in rows:
        if transaction_id in seen_ids:
            continue
        seen_ids.add(transaction_id)
        balances[account] = balances.get(account, Decimal("0")) + Decimal(amount_text)

    quantum = Decimal("0.01")
    output = []
    for account in sorted(balances):
        rounded = balances[account].quantize(quantum, rounding=ROUND_HALF_EVEN)
        if rounded == 0:
            rounded = Decimal("0.00")
        output.append([account, format(rounded, ".2f")])
    return output
