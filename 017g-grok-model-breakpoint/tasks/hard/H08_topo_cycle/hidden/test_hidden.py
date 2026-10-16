import pytest
from schedule import plan, CycleError

def test_isolates_are_alphabetical():
    assert plan(["c", "a", "b"], []) == ["a", "b", "c"]

def test_tie_break_on_a_diamond():
    assert plan(["c", "b", "a"], [("a", "c"), ("b", "c")]) == ["a", "b", "c"]

def test_duplicate_edge_is_one_edge():
    assert plan(["b", "a"], [("a", "b"), ("a", "b")]) == ["a", "b"]

def test_self_loop_and_unknown():
    with pytest.raises(CycleError):
        plan(["a"], [("a", "a")])
    with pytest.raises(ValueError):
        plan(["a"], [("a", "missing")])
