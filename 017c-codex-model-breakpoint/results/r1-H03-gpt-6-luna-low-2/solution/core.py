from decimal import Decimal, ROUND_HALF_EVEN

def solve(rows):
    totals = {}
    seen_ids = set()
    for row in rows:
        account, amount, row_id = row
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)
        totals[account] = totals.get(account, Decimal(0)) + Decimal(amount)

    quantum = Decimal("0.01")
    result = []
    for account in sorted(totals):
        balance = totals[account].quantize(quantum, rounding=ROUND_HALF_EVEN)
        if balance == 0:
            balance = Decimal("0.00")
        result.append([account, format(balance, ".2f")])
    return result
