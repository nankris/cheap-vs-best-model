from tariffs import degree_day_charge
from units import c_to_f

def day_line(celsius: float, rate: float) -> dict:
    return {"temp_f": c_to_f(celsius), "charge": degree_day_charge(celsius, rate)}

def month_total(days: list) -> float:
    return sum(degree_day_charge(c, r) for c, r in days)
