from money import as_number

def total_tax(amounts, rate):
    total = sum(as_number(amount) * as_number(rate) for amount in amounts)
    return f"{round(total, 2):.2f}"
