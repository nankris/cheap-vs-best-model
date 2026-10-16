from checkout import total

def test_single_fifteen_percent():
    assert total(8000, [{"percent": 15}]) == 6800
