from units import c_to_f

def degree_day_charge(celsius: float, rate: float) -> float:
    fahrenheit = c_to_f(celsius)
    extra = fahrenheit - 60.0
    if extra < 0:
        extra = 0.0
    return extra * rate
