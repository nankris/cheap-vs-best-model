import pytest
from defaults import DEFAULTS
from loader import load
from merge import deep_merge

def test_none_deletes_top_and_nested():
    got = load({"debug": None, "db": {"name": None}})
    assert "debug" not in got
    assert got["db"] == {"host": "localhost", "port": 5432}
    assert got["tags"] == ["default"]

def test_none_deletes_whole_section_and_lists_replace():
    got = load({"db": None, "tags": ["a", "b"]})
    assert "db" not in got
    assert got["tags"] == ["a", "b"]

def test_copy_and_unknown_key_and_types():
    got = load({})
    got["db"]["host"] = "mutated"
    got["tags"].append("nope")
    assert DEFAULTS["db"]["host"] == "localhost"
    assert DEFAULTS["tags"] == ["default"]
    with pytest.raises(ValueError):
        load({"extra": 1})
    with pytest.raises(ValueError):
        load({"service": 3})
    with pytest.raises(ValueError):
        load({"limits": {"max_conn": "10"}})
    # a new nested key is allowed
    assert load({"db": {"ssl": True}})["db"]["ssl"] is True

def test_merge_does_not_alias_base():
    base = {"db": {"port": 1}, "tags": ["x"]}
    got = deep_merge(base, {"db": {"host": "h"}})
    got["db"]["port"] = 9
    got["tags"].append("y")
    assert base == {"db": {"port": 1}, "tags": ["x"]}
