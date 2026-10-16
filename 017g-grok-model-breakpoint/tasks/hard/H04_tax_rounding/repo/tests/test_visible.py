from invoice import total_tax

def test_two_half_lines_round_before_the_sum():
    assert total_tax(["1.005", "1.005"], "1") == "2.00"
