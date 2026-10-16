from report import day_line

def test_one_warm_day():
    assert day_line(20, 1.5) == {"temp_f": 68.0, "charge": 12.0}
