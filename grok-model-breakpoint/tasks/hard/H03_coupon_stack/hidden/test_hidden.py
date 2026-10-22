from decimal import Decimal
import pytest
from coupon import fraction
from checkout import total

def test_fraction_and_apply():
    from pricing import apply_fraction
    assert fraction({"percent": 15}) == Decimal("0.15")
    assert apply_fraction(8000, Decimal("0.15")) == 6800

def test_stack_is_multiplicative():
    assert total(8000, [{"percent": 10}, {"percent": 10}]) == 6480

def test_full_and_empty_and_zero():
    assert total(8000, [{"percent": 100}]) == 0
    assert total(8000, []) == 8000
    assert total(8000, [{"percent": 0}]) == 8000

def test_half_even_end_round():
    # 100 cents, 15% off = 85 exactly. 33 cents * 50% = 16.5 -> 16 (half-even, 6 is even? )
    # 1 * 0.5 = 0.5 -> 0 or 1? half-even to even integer: 0 is even, so 0.
    assert total(1, [{"percent": 50}]) == 0
    # 3 * 0.5 = 1.5 -> 2 because 1 is odd.
    assert total(3, [{"percent": 50}]) == 2

def test_bad_percent():
    with pytest.raises(ValueError):
        total(8000, [{"percent": 150}])
    with pytest.raises(ValueError):
        total(8000, [{"percent": -1}])
