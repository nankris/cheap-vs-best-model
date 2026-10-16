import json
from decimal import Decimal, ROUND_HALF_EVEN


def present(value):
    result = []
    for account, balance in value:
        rounded = balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        if rounded == 0:
            rounded = abs(rounded)
        result.append([account, format(rounded, ".2f")])
    return json.dumps(result)
