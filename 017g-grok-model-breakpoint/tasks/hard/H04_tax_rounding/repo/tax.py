from money import as_number

def line_tax(amount, rate):
    return f"{round(as_number(amount) * as_number(rate), 2):.2f}"
