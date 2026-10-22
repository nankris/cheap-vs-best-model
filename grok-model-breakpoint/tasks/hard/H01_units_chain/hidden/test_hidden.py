from units import c_to_f
from tariffs import degree_day_charge
from report import day_line, month_total

def test_anchors():
    assert c_to_f(-40) == -40.0
    assert c_to_f(0) == 32.0
    assert c_to_f(100) == 212.0

def test_below_base_is_free():
    assert degree_day_charge(10, 2) == 0.0
    assert day_line(10, 2) == {"temp_f": 50.0, "charge": 0.0}

def test_month_mix():
    days = [(25, 1.0), (10, 4.0), (20, 1.5)]
    # 25C = 77F -> 17; 10C = 50F -> 0; 20C = 68F -> 12
    assert month_total(days) == 17.0 + 0.0 + 12.0
