from pipeline import run

def test_one_clean_row():
    got = run([{"id": "1", "name": "Ada", "qty": "2"}])
    assert got["skipped"] == 0
    assert got["rows"] == {"1": {"name": "Ada", "qty": 2}}
