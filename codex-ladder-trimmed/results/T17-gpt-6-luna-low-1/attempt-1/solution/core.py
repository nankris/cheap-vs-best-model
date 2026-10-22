from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN, localcontext


def solve(rows):
    """Aggregate unique transaction ids into exact, rounded account balances."""
    rows = list(rows)
    # Decimal arithmetic obeys the active context precision. Size it from the
    # input so adding valid long decimal strings cannot silently round early.
    precision = max(28, sum(len(amount.replace(".", "").lstrip("+-")) for _, amount, _ in rows) + 4)
    seen = set()
    totals = defaultdict(Decimal)

    with localcontext() as context:
        context.prec = precision
        for account, amount_text, transaction_id in rows:
            if transaction_id in seen:
                continue
            seen.add(transaction_id)
            totals[account] += Decimal(amount_text)

        result = []
        for account in sorted(totals):
            rounded = totals[account].quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            if rounded == 0:
                rounded = Decimal("0.00")
            result.append([account, format(rounded, ".2f")])
    return result
