import pytest
from weeks import week_key
from rollup import sum_by_week
from dates import parse_iso

def test_year_boundary():
    assert week_key("2024-12-29") == "2024-W52"
    assert week_key("2024-12-30") == "2025-W01"
    assert week_key("2025-01-01") == "2025-W01"
    assert week_key("2021-01-01") == "2020-W53"

def test_boundary_bucket():
    assert sum_by_week([("2024-12-30", 1), ("2025-01-01", 2), ("2024-12-29", 4)]) == {
        "2025-W01": 3,
        "2024-W52": 4,
    }

def test_bad_date():
    with pytest.raises(ValueError):
        parse_iso("2024-13-40")
    with pytest.raises(ValueError):
        week_key("nope")
