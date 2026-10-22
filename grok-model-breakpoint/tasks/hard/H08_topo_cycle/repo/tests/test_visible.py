import pytest
from schedule import plan, CycleError

def test_cycle_raises():
    with pytest.raises(CycleError):
        plan(["a", "b"], [("a", "b"), ("b", "a")])
