from rollup import sum_by_week

def test_midyear_wednesday_and_thursday():
    assert sum_by_week([("2024-06-12", 5), ("2024-06-13", 7)]) == {"2024-W24": 12}
