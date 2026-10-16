import importlib.util
from pathlib import Path
from pipeline import run

def test_legacy_module_is_gone():
    assert importlib.util.find_spec("legacy") is None
    assert not Path("legacy.py").exists()

def test_last_duplicate_wins_and_whitespace():
    got = run([
        {"id": "1", "name": "first", "qty": "1"},
        {"id": " 1 ", "name": " Ada ", "qty": " 4 "},
    ])
    assert got["skipped"] == 0
    assert got["rows"] == {"1": {"name": "Ada", "qty": 4}}

def test_skips_do_not_raise():
    got = run([
        {"id": "2", "name": "Bea", "qty": "3"},
        {"id": "3", "name": "Cy", "qty": "-1"},
        {"id": "", "name": "No", "qty": "1"},
        {"id": "4", "name": "   ", "qty": "1"},
        {"id": "5", "name": "Dee", "qty": "x"},
        "not-a-dict",
        None,
    ])
    assert got["rows"] == {"2": {"name": "Bea", "qty": 3}}
    assert got["skipped"] == 6
