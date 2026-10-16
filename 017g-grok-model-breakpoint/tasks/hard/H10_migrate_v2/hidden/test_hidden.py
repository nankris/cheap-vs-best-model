import pytest
from reader import load
from schema import is_v2

def test_extra_field_whitespace_and_missing_age():
    got = load({"full_name": "  Ada  ", "city": "London", "note": "x"})
    assert got == {"name": "Ada", "city": "London", "note": "x", "version": 2}
    assert is_v2(got)

def test_already_v2_is_unchanged():
    original = {"version": 2, "name": "  Ada  ", "age": 36, "extra": [1]}
    got = load(original)
    assert got == original
    assert got is not original
    again = load({"version": 2, "name": "Bea", "age": "36"})
    assert again["age"] == "36"
    assert again["name"] == "Bea"

def test_errors():
    with pytest.raises(ValueError):
        load({"full_name": "   ", "age": "1"})
    with pytest.raises(ValueError):
        load({"full_name": "Ada", "age": "36y"})
    with pytest.raises(ValueError):
        load({"version": 2, "age": 1})
    with pytest.raises(ValueError):
        load(["Ada"])
