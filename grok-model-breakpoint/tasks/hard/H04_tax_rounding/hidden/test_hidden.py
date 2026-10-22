import pytest
from tax import line_tax
from invoice import total_tax

def test_half_even_lines():
    assert line_tax("1.225", "1") == "1.22"
    assert line_tax("1.275", "1") == "1.28"
    assert line_tax("0.005", "1") == "0.00"

def test_sum_of_rounded_lines():
    assert total_tax(["1.225", "1.275"], "1") == "2.50"
    assert total_tax(["10.00"], "0.1225") == "1.22"

def test_empty_and_invalid():
    assert total_tax([], "0.0825") == "0.00"
    with pytest.raises(ValueError):
        line_tax("nope", "1")
    with pytest.raises(ValueError):
        total_tax(["1.00", "x"], "0.1")
