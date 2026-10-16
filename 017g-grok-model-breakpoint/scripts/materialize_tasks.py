#!/usr/bin/env python3
"""Write the hard-task repos, hidden tests, and reference fixes. Copy 5 easy tasks from 017."""
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARD = ROOT / "tasks" / "hard"
EASY = ROOT / "tasks" / "easy"
SUITE = Path("/workspace/work/tig/_harness/fixtures/SUITE14")
EASY_NAMES = ["N01_median", "N02_duration", "N03_csv", "T02_duplicate", "T07_multihunk"]


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def dump_task(name, repo, hidden, fixed, remove=None):
    base = HARD / name
    if base.exists():
        shutil.rmtree(base)
    for rel, body in repo.items():
        write(base / "repo" / rel, body)
    for rel, body in hidden.items():
        write(base / "hidden" / rel, body)
    for rel, body in fixed.items():
        write(base / "fixed" / rel, body)
    if remove:
        write(base / "remove_before_grade.txt", "\n".join(remove) + "\n")


def h01():
    spec = """
    # Meter day charges

    Three modules. `report` calls `tariffs`, which calls `units`. Fix the program so this contract holds. Do not special-case the numbers in the visible test.

    - `units.c_to_f(celsius)` returns Fahrenheit: `celsius * 9/5 + 32`.
    - `tariffs.degree_day_charge(celsius, rate)` converts with `c_to_f`. The charge is `rate` dollars for each degree Fahrenheit above 60. At or below 60F the charge is 0.
    - `report.day_line(celsius, rate)` returns `{"temp_f": <fahrenheit>, "charge": <dollars>}`.
    - `report.month_total(days)` takes a list of `(celsius, rate)` pairs and returns the sum of the degree-day charges.

    Examples that the visible test does not cover: `c_to_f(-40) == -40`, `c_to_f(0) == 32`, `c_to_f(100) == 212`, `degree_day_charge(10, 2) == 0` (50F), `degree_day_charge(25, 1) == 17`.
    """
    repo = {
        "SPEC.md": spec,
        "units.py": """
def c_to_f(celsius: float) -> float:
    # Converts a Celsius reading for the billing report.
    return celsius * 9.0 / 5.0
""",
        "tariffs.py": """
from units import c_to_f

def degree_day_charge(celsius: float, rate: float) -> float:
    fahrenheit = c_to_f(celsius)
    extra = fahrenheit - 60.0
    if extra < 0:
        extra = 0.0
    return extra * rate
""",
        "report.py": """
from tariffs import degree_day_charge
from units import c_to_f

def day_line(celsius: float, rate: float) -> dict:
    return {"temp_f": c_to_f(celsius), "charge": degree_day_charge(celsius, rate)}

def month_total(days: list) -> float:
    return sum(degree_day_charge(c, r) for c, r in days)
""",
        "tests/test_visible.py": """
from report import day_line

def test_one_warm_day():
    assert day_line(20, 1.5) == {"temp_f": 68.0, "charge": 12.0}
""",
    }
    hidden = {
        "test_hidden.py": """
from units import c_to_f
from tariffs import degree_day_charge
from report import day_line, month_total

def test_anchors():
    assert c_to_f(-40) == -40.0
    assert c_to_f(0) == 32.0
    assert c_to_f(100) == 212.0

def test_below_base_is_free():
    assert degree_day_charge(10, 2) == 0.0
    assert day_line(10, 2) == {"temp_f": 50.0, "charge": 0.0}

def test_month_mix():
    days = [(25, 1.0), (10, 4.0), (20, 1.5)]
    # 25C = 77F -> 17; 10C = 50F -> 0; 20C = 68F -> 12
    assert month_total(days) == 17.0 + 0.0 + 12.0
"""
    }
    fixed = {
        "units.py": """
def c_to_f(celsius: float) -> float:
    return celsius * 9.0 / 5.0 + 32.0
"""
    }
    dump_task("H01_units_chain", repo, hidden, fixed)


def h02():
    spec = """
    # Split the importer

    `legacy.py` is the old importer. It is not the specification. Build three modules and stop calling legacy:

    - `parse.py` defines `parse_rows(records)`.
    - `store.py` defines `upsert(parsed_rows)`.
    - `pipeline.py` defines `run(records)` and returns `{"rows": {...}, "skipped": <int>}`.

    The grader deletes `legacy.py` before scoring. `run` must not import it.

    Each record is a dict with `id`, `name`, and `qty`. Contract:

    - Strip leading and trailing whitespace on `id`, `name`, and `qty` before use.
    - `qty` is an integer. `id` and `name` are strings and must be non-empty after stripping.
    - A row with a negative qty, a blank id, a blank name, a non-integer qty, or a non-dict record is skipped. It does not raise.
    - When the same `id` appears twice, the later row wins.
    - `rows` maps id to `{"name": <stripped name>, "qty": <int>}`.
    - `skipped` counts every skipped record. Well-formed records that were overwritten are not skips.

    The visible test has one clean row. Match the whole contract, not only that row.
    """
    repo = {
        "SPEC.md": spec,
        "legacy.py": """
def parse_and_store(records):
    out = {}
    for rec in records:
        id_ = rec["id"]
        if id_ in out:
            continue
        qty = int(rec["qty"])
        if qty < 0:
            raise ValueError("negative")
        out[id_] = {"name": rec["name"], "qty": qty}
    return {"rows": out, "skipped": 0}
""",
        "tests/test_visible.py": """
from pipeline import run

def test_one_clean_row():
    got = run([{"id": "1", "name": "Ada", "qty": "2"}])
    assert got["skipped"] == 0
    assert got["rows"] == {"1": {"name": "Ada", "qty": 2}}
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "parse.py": """
def parse_rows(records):
    parsed = []
    skipped = 0
    for rec in records:
        if not isinstance(rec, dict):
            skipped += 1
            continue
        id_ = str(rec.get("id", "")).strip()
        name = str(rec.get("name", "")).strip()
        raw_qty = str(rec.get("qty", "")).strip()
        if id_ == "" or name == "":
            skipped += 1
            continue
        try:
            qty = int(raw_qty)
        except ValueError:
            skipped += 1
            continue
        if qty < 0:
            skipped += 1
            continue
        parsed.append({"id": id_, "name": name, "qty": qty})
    return parsed, skipped
""",
        "store.py": """
def upsert(parsed_rows):
    out = {}
    for row in parsed_rows:
        out[row["id"]] = {"name": row["name"], "qty": row["qty"]}
    return out
""",
        "pipeline.py": """
from parse import parse_rows
from store import upsert

def run(records):
    parsed, skipped = parse_rows(records)
    return {"rows": upsert(parsed), "skipped": skipped}
""",
    }
    dump_task("H02_refactor_split", repo, hidden, fixed, remove=["legacy.py"])


def h03():
    spec = """
    # Coupon checkout

    Prices are integer cents. A coupon is a dict `{"percent": N}` where N is an integer from 0 through 100 meaning N percent off. Anything else raises `ValueError`.

    - `coupon.fraction(coupon)` returns the fraction off as a `decimal.Decimal`, so 15 becomes `Decimal("0.15")`.
    - `pricing.apply_fraction(price_cents, fraction)` multiplies the price by `(1 - fraction)`.
    - `checkout.total(price_cents, coupons)` applies every coupon, multiplicatively, in order. Round half-even to the nearest cent only once, at the end. No coupons returns the price unchanged. A 100 percent coupon returns 0.

    Two 10 percent coupons on 8000 cents is 6480, not 6400. One 15 percent coupon on 8000 cents is 6800. The visible test only checks the single 15 percent coupon.
    """
    repo = {
        "SPEC.md": spec,
        "coupon.py": """
def fraction(coupon):
    return coupon["percent"]
""",
        "pricing.py": """
def apply_fraction(price_cents, fraction):
    return price_cents * (1 - fraction)
""",
        "checkout.py": """
from coupon import fraction as coupon_fraction
from pricing import apply_fraction

def total(price_cents, coupons):
    off = 0
    for coupon in coupons:
        off += coupon_fraction(coupon)
    return apply_fraction(price_cents, off)
""",
        "tests/test_visible.py": """
from checkout import total

def test_single_fifteen_percent():
    assert total(8000, [{"percent": 15}]) == 6800
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "coupon.py": """
from decimal import Decimal

def fraction(coupon):
    percent = coupon["percent"]
    if not isinstance(percent, int) or isinstance(percent, bool) or not 0 <= percent <= 100:
        raise ValueError("percent")
    return Decimal(percent) / Decimal(100)
""",
        "pricing.py": """
from decimal import Decimal, ROUND_HALF_EVEN

def apply_fraction(price_cents, fraction):
    value = Decimal(price_cents) * (Decimal(1) - Decimal(fraction))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
""",
        "checkout.py": """
from decimal import Decimal, ROUND_HALF_EVEN
from coupon import fraction as coupon_fraction

def total(price_cents, coupons):
    if not isinstance(price_cents, int) or isinstance(price_cents, bool):
        raise ValueError("price")
    value = Decimal(price_cents)
    for coupon in coupons:
        frac = coupon_fraction(coupon)
        value = value * (Decimal(1) - frac)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
""",
    }
    dump_task("H03_coupon_stack", repo, hidden, fixed)


def h04():
    spec = """
    # Per-line tax

    Amounts and the rate are decimal strings. Use `decimal.Decimal`. Do not use binary floats.

    - `tax.line_tax(amount, rate)` returns the tax as a two-place string. Multiply, then quantize to cents with `ROUND_HALF_EVEN`.
    - `invoice.total_tax(amounts, rate)` sums the already-rounded line taxes and returns that sum as a two-place string. Rounding each line and rounding the sum are different. The contract is per line, then sum.
    - An empty list totals `"0.00"`. A non-decimal string raises `ValueError`.

    `total_tax(["1.005", "1.005"], "1")` is `"2.00"` because each line is `1.00`. It is not `"2.01"`.
    `line_tax("1.225", "1")` is `"1.22"`. `line_tax("1.275", "1")` is `"1.28"`. `line_tax("0.005", "1")` is `"0.00"`.
    `total_tax(["10.00"], "0.1225")` is `"1.22"`.

    The visible test only checks the two `1.005` lines.
    """
    repo = {
        "SPEC.md": spec,
        "money.py": """
def as_number(text):
    return float(text)
""",
        "tax.py": """
from money import as_number

def line_tax(amount, rate):
    return f"{round(as_number(amount) * as_number(rate), 2):.2f}"
""",
        "invoice.py": """
from money import as_number

def total_tax(amounts, rate):
    total = sum(as_number(amount) * as_number(rate) for amount in amounts)
    return f"{round(total, 2):.2f}"
""",
        "tests/test_visible.py": """
from invoice import total_tax

def test_two_half_lines_round_before_the_sum():
    assert total_tax(["1.005", "1.005"], "1") == "2.00"
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "money.py": """
from decimal import Decimal

def as_decimal(text):
    try:
        return Decimal(text)
    except Exception as exc:
        raise ValueError(text) from exc
""",
        "tax.py": """
from decimal import Decimal, ROUND_HALF_EVEN
from money import as_decimal

def line_tax(amount, rate):
    value = as_decimal(amount) * as_decimal(rate)
    cents = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return format(cents, "f")
""",
        "invoice.py": """
from decimal import Decimal
from tax import line_tax

def total_tax(amounts, rate):
    total = sum((Decimal(line_tax(amount, rate)) for amount in amounts), Decimal("0"))
    return format(total.quantize(Decimal("0.01")), "f")
""",
    }
    dump_task("H04_tax_rounding", repo, hidden, fixed)


def h05():
    spec = """
    # ISO weeks

    Dates are civil `YYYY-MM-DD` strings, not timestamps.

    - `dates.parse_iso` returns a `datetime.date` or raises `ValueError`.
    - `weeks.week_key` returns the ISO-8601 week as `"{iso_year}-W{iso_week:02d}"`. The week starts on Monday. Use the ISO year, which is not always the calendar year.
    - `rollup.sum_by_week(rows)` takes `(date_string, amount_int)` pairs and returns a dict of week key to summed amount.

    Anchors the visible test does not use:

    - `2024-12-29` → `2024-W52`
    - `2024-12-30` → `2025-W01`
    - `2025-01-01` → `2025-W01`
    - `2021-01-01` → `2020-W53`

    A Sunday-start week number is wrong even when the two dates fall in the same bucket.
    """
    repo = {
        "SPEC.md": spec,
        "dates.py": """
import datetime as dt

def parse_iso(text):
    try:
        year, month, day = (int(part) for part in text.split("-"))
        return dt.date(year, month, day)
    except Exception as exc:
        raise ValueError(text) from exc
""",
        "weeks.py": """
import datetime as dt
from dates import parse_iso

def week_key(iso_date):
    day = parse_iso(iso_date)
    since_sunday = (day.weekday() + 1) % 7
    start = day - dt.timedelta(days=since_sunday)
    week = int(start.strftime("%U"))
    return f"{start.year}-W{week:02d}"
""",
        "rollup.py": """
from weeks import week_key

def sum_by_week(rows):
    totals = {}
    for iso_date, amount in rows:
        key = week_key(iso_date)
        totals[key] = totals.get(key, 0) + amount
    return totals
""",
        "tests/test_visible.py": """
from rollup import sum_by_week

def test_midyear_wednesday_and_thursday():
    assert sum_by_week([("2024-06-12", 5), ("2024-06-13", 7)]) == {"2024-W24": 12}
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "weeks.py": """
from dates import parse_iso

def week_key(iso_date):
    day = parse_iso(iso_date)
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
"""
    }
    dump_task("H05_iso_week", repo, hidden, fixed)


def h06():
    spec = """
    # Config merge

    `defaults.DEFAULTS` is the base config. `merge.deep_merge(base, override)` must:

    - Merge nested dicts. An override key replaces only itself. Sibling keys stay.
    - Replace lists and scalars. Lists are not concatenated.
    - Treat `None` as delete. `{"debug": None}` removes `debug`. `{"db": {"name": None}}` removes only `db.name`. `{"db": None}` removes `db`.
    - Return a deep copy. Mutating the result must not change `base` or `DEFAULTS`.

    `loader.load(override)` merges `DEFAULTS` with `override` and rejects unknown top-level keys with `ValueError`. Known top-level keys are `service`, `debug`, `db`, `limits`, and `tags`. Nested keys inside `db` and `limits` may be new. `service`, when present, must be a string. `limits.max_conn`, when present, must be an int. A bad type raises `ValueError`.

    The visible test only overrides `db.port`.
    """
    repo = {
        "SPEC.md": spec,
        "defaults.py": """
DEFAULTS = {
    "service": "billing",
    "debug": False,
    "db": {"host": "localhost", "port": 5432, "name": "app"},
    "limits": {"max_conn": 10, "timeout_s": 5},
    "tags": ["default"],
}
""",
        "merge.py": """
def deep_merge(base, override):
    out = dict(base)
    out.update(override)
    return out
""",
        "loader.py": """
from defaults import DEFAULTS
from merge import deep_merge

def load(override):
    return deep_merge(DEFAULTS, override)
""",
        "tests/test_visible.py": """
from loader import load

def test_nested_port_keeps_siblings():
    got = load({"db": {"port": 5433}})
    assert got["db"] == {"host": "localhost", "port": 5433, "name": "app"}
    assert got["service"] == "billing"
    assert got["debug"] is False
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "merge.py": """
def _copy(value):
    if isinstance(value, dict):
        return {key: _copy(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return list(value)
    return value

def deep_merge(base, override):
    if not isinstance(override, dict):
        raise ValueError("override")
    out = _copy(base) if isinstance(base, dict) else {}
    for key, value in override.items():
        if value is None:
            out.pop(key, None)
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = _copy(value)
    return out
""",
        "loader.py": """
from defaults import DEFAULTS
from merge import deep_merge

ALLOWED = {"service", "debug", "db", "limits", "tags"}

def load(override):
    if not isinstance(override, dict):
        raise ValueError("override")
    for key in override:
        if key not in ALLOWED:
            raise ValueError(key)
    merged = deep_merge(DEFAULTS, override)
    if "service" in merged and not isinstance(merged["service"], str):
        raise ValueError("service")
    limits = merged.get("limits")
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits")
        if "max_conn" in limits and (
            not isinstance(limits["max_conn"], int) or isinstance(limits["max_conn"], bool)
        ):
            raise ValueError("max_conn")
    return merged
""",
    }
    dump_task("H06_deep_merge", repo, hidden, fixed)


def h07():
    spec = """
    # View cache

    `compute.build(user, include_archived=False, role="viewer")` is the expensive function. It appends:

    - `"<user>:active"` always
    - `"<user>:archived"` when `include_archived` is true
    - `"<user>:secret"` when `role` is `"admin"`

    `views.get_view(user, include_archived=False, role="viewer")` returns that list, cached. The cache key is the user, the archived flag, and the role. Different combinations must not share an entry.

    - A repeat call with the same arguments must not call `compute.build` again.
    - `views.call_count()` is the number of `compute.build` calls since `views.clear()`.
    - `views.bust(user)` drops every cached entry for that user and no other user.
    - `views.clear()` drops the whole cache and resets the counter.

    The visible test calls `ada` twice with different `include_archived` values and expects two computes. It never asks for `role="admin"` and never calls `bust`.
    """
    repo = {
        "SPEC.md": spec,
        "compute.py": """
def build(user, include_archived=False, role="viewer"):
    rows = [f"{user}:active"]
    if include_archived:
        rows.append(f"{user}:archived")
    if role == "admin":
        rows.append(f"{user}:secret")
    return rows
""",
        "cache.py": """
class Cache:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        self._data[key] = value

    def drop_user(self, user):
        # Drops an entry only when the key is exactly the user id.
        self._data.pop(user, None)

    def clear(self):
        self._data.clear()
""",
        "views.py": """
from cache import Cache
from compute import build

_cache = Cache()
_calls = {"n": 0}

def clear():
    _cache.clear()
    _calls["n"] = 0

def call_count():
    return _calls["n"]

def bust(user):
    _cache.drop_user(user)

def get_view(user, include_archived=False, role="viewer"):
    key = user
    hit = _cache.get(key)
    if hit is not None:
        return hit
    _calls["n"] += 1
    rows = build(user, include_archived=include_archived, role=role)
    _cache.put(key, rows)
    return rows
""",
        "tests/test_visible.py": """
from views import get_view, clear, call_count

def test_archived_flag_is_part_of_the_key():
    clear()
    first = get_view("ada", include_archived=False)
    second = get_view("ada", include_archived=True)
    assert first == ["ada:active"]
    assert second == ["ada:active", "ada:archived"]
    assert call_count() == 2
""",
    }
    hidden = {
        "test_hidden.py": """
from views import get_view, clear, call_count, bust

def test_role_is_part_of_the_key_and_hits_are_free():
    clear()
    viewer = get_view("ada", role="viewer")
    admin = get_view("ada", role="admin")
    again = get_view("ada", role="admin")
    assert viewer == ["ada:active"]
    assert admin == ["ada:active", "ada:secret"]
    assert again == ["ada:active", "ada:secret"]
    assert call_count() == 2

def test_bust_one_user_and_keep_the_other():
    clear()
    get_view("ada", include_archived=True, role="admin")
    get_view("bea", include_archived=False)
    assert call_count() == 2
    bust("ada")
    get_view("bea", include_archived=False)
    assert call_count() == 2
    refreshed = get_view("ada", include_archived=True, role="admin")
    assert refreshed == ["ada:active", "ada:archived", "ada:secret"]
    assert call_count() == 3

def test_users_do_not_collide():
    clear()
    assert get_view("ada") == ["ada:active"]
    assert get_view("bea", include_archived=True) == ["bea:active", "bea:archived"]
    assert call_count() == 2
"""
    }
    fixed = {
        "cache.py": """
class Cache:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        self._data[key] = value

    def drop_user(self, user):
        for key in list(self._data):
            owner = key[0] if isinstance(key, tuple) else key
            if owner == user:
                del self._data[key]

    def clear(self):
        self._data.clear()
""",
        "views.py": """
from cache import Cache
from compute import build

_cache = Cache()
_calls = {"n": 0}

def clear():
    _cache.clear()
    _calls["n"] = 0

def call_count():
    return _calls["n"]

def bust(user):
    _cache.drop_user(user)

def get_view(user, include_archived=False, role="viewer"):
    key = (user, bool(include_archived), role)
    hit = _cache.get(key)
    if hit is not None:
        return list(hit)
    _calls["n"] += 1
    rows = build(user, include_archived=include_archived, role=role)
    _cache.put(key, list(rows))
    return list(rows)
""",
    }
    dump_task("H07_cache_key", repo, hidden, fixed)


def h08():
    spec = """
    # Build order

    `schedule.plan(nodes, edges)` returns a list. `edges` are `(before, after)` pairs: `before` must appear earlier than `after`. `schedule.CycleError` is the error type.

    - Every name in `nodes` appears exactly once. A name with no edges is included.
    - Duplicate edges count once.
    - An edge that names something outside `nodes` raises `ValueError`.
    - A cycle, including a self-loop, raises `CycleError`. Do not return a partial list.
    - When several nodes are ready, pick the lexicographically smallest name.

    The visible test is a two-node cycle. It does not check isolated nodes, ties, duplicate edges, or a self-loop.
    """
    repo = {
        "SPEC.md": spec,
        "graph.py": """
def normalize(nodes, edges):
    return list(nodes), list(edges)
""",
        "topo.py": """
class CycleError(Exception):
    pass

def topo_sort(nodes, edges):
    adj = {}
    indeg = {}
    for before, after in edges:
        adj.setdefault(before, []).append(after)
        indeg.setdefault(before, 0)
        indeg[after] = indeg.get(after, 0) + 1
    queue = [name for name, degree in indeg.items() if degree == 0]
    order = []
    while queue:
        name = queue.pop(0)
        order.append(name)
        for nxt in adj.get(name, []):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return order
""",
        "schedule.py": """
from graph import normalize
from topo import topo_sort, CycleError

def plan(nodes, edges):
    nodes, edges = normalize(nodes, edges)
    return topo_sort(nodes, edges)
""",
        "tests/test_visible.py": """
import pytest
from schedule import plan, CycleError

def test_cycle_raises():
    with pytest.raises(CycleError):
        plan(["a", "b"], [("a", "b"), ("b", "a")])
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "topo.py": """
import heapq

class CycleError(Exception):
    pass

def topo_sort(nodes, edges):
    node_list = list(nodes)
    if len(set(node_list)) != len(node_list):
        raise ValueError("duplicate node")
    adj = {name: [] for name in node_list}
    indeg = {name: 0 for name in node_list}
    seen = set()
    for before, after in edges:
        if before not in indeg or after not in indeg:
            raise ValueError("unknown node")
        if (before, after) in seen:
            continue
        seen.add((before, after))
        adj[before].append(after)
        indeg[after] += 1
    ready = [name for name in node_list if indeg[name] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        name = heapq.heappop(ready)
        order.append(name)
        for nxt in adj[name]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(ready, nxt)
    if len(order) != len(node_list):
        raise CycleError("cycle")
    return order
"""
    }
    dump_task("H08_topo_cycle", repo, hidden, fixed)


def h09():
    spec = """
    # Token match

    `match.matches(query, text)` is true when every query token occurs in the text. Order does not matter. Extra text tokens are fine.

    Token rules, shared by query and text:

    - Split on whitespace only. A hyphenated word is one token. `state` does not match `state-of-the-art`.
    - Strip leading and trailing `.,;:!?"'\\`()[]{}` from each token. A trailing comma must not keep two equal words apart.
    - Then Unicode-casefold and NFC-normalize. `café` matches `Cafe` plus a combining acute accent. `straße` matches `STRASSE`.

    `normalize.normalize_token` and `tokens.tokenize` own those steps. `match.matches` must use them.

    The visible test is the `café` case only.
    """
    repo = {
        "SPEC.md": spec,
        "normalize.py": """
def normalize_token(token):
    return token.lower()
""",
        "tokens.py": """
from normalize import normalize_token

def tokenize(text):
    return [normalize_token(part) for part in text.split() if part]
""",
        "match.py": """
from tokens import tokenize

def matches(query, text):
    wanted = tokenize(query)
    have = tokenize(text)
    return all(token in have for token in wanted)
""",
        "tests/test_visible.py": """
from match import matches

def test_composed_and_decomposed_cafe():
    assert matches("café", "Cafe\\u0301 menu") is True
""",
    }
    hidden = {
        "test_hidden.py": """
from match import matches

def test_sharp_s_casefold():
    assert matches("straße", "the STRASSE opens at nine") is True

def test_hyphen_is_one_token():
    assert matches("state", "state-of-the-art design") is False
    assert matches("state-of-the-art", "This is state-of-the-art.") is True

def test_edge_punctuation_and_order():
    assert matches("hello", "well, hello, world") is True
    assert matches("world hello", "hello world") is True
    assert matches("missing", "hello world") is False
"""
    }
    fixed = {
        "normalize.py": """
import unicodedata

_EDGES = ".,;:!?" + "'" + '"' + "`()[]{}"

def normalize_token(token):
    stripped = token.strip(_EDGES)
    return unicodedata.normalize("NFC", stripped.casefold())
""",
        "tokens.py": """
from normalize import normalize_token

def tokenize(text):
    out = []
    for part in str(text).split():
        token = normalize_token(part)
        if token:
            out.append(token)
    return out
""",
    }
    dump_task("H09_unicode_match", repo, hidden, fixed)


def h10():
    spec = """
    # Record migration

    `schema.is_v2(record)` is true only when `record` is a dict and `record["version"] == 2`.

    `migrate.to_v2(record)`:

    - If the record is already v2, return a shallow copy unchanged. Do not rename or retype fields.
    - Otherwise treat it as v1. Copy unknown keys through, except do not keep `full_name`.
    - `full_name` becomes `name` with surrounding whitespace stripped. An empty name raises `ValueError`.
    - A present `age` must be a string of digits (no sign, no spaces after stripping the string) and becomes an `int`. A missing `age` stays missing. A bad `age` raises `ValueError`.
    - Set `version` to `2`.

    `reader.load(record)` returns `to_v2(record)`. A v2 record with a missing or blank `name` raises `ValueError`. A non-dict raises `ValueError`.

    The visible test is one ordinary v1 record: full name `Ada`, age `"36"`, city `London`.
    """
    repo = {
        "SPEC.md": spec,
        "schema.py": """
def is_v2(record):
    return isinstance(record, dict) and record.get("version") == 2
""",
        "migrate.py": """
def to_v2(record):
    out = dict(record)
    out["version"] = 2
    return out
""",
        "reader.py": """
from migrate import to_v2

def load(record):
    return to_v2(record)
""",
        "tests/test_visible.py": """
from reader import load

def test_v1_ada():
    got = load({"full_name": "Ada", "age": "36", "city": "London"})
    assert got["name"] == "Ada"
    assert got["age"] == 36
    assert got["city"] == "London"
    assert got["version"] == 2
    assert "full_name" not in got
""",
    }
    hidden = {
        "test_hidden.py": """
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
"""
    }
    fixed = {
        "migrate.py": """
from schema import is_v2

def to_v2(record):
    if not isinstance(record, dict):
        raise ValueError("record")
    if is_v2(record):
        return dict(record)
    out = {}
    for key, value in record.items():
        if key in ("full_name", "age", "version"):
            continue
        out[key] = value
    name = str(record.get("full_name", "")).strip()
    if name == "":
        raise ValueError("name")
    out["name"] = name
    if "age" in record:
        age_text = str(record["age"]).strip()
        if not age_text.isdigit():
            raise ValueError("age")
        out["age"] = int(age_text)
    out["version"] = 2
    return out
""",
        "reader.py": """
from migrate import to_v2

def load(record):
    if not isinstance(record, dict):
        raise ValueError("record")
    migrated = to_v2(record)
    name = migrated.get("name")
    if not isinstance(name, str) or name.strip() == "":
        raise ValueError("name")
    return migrated
""",
    }
    dump_task("H10_migrate_v2", repo, hidden, fixed)


def easy():
    if EASY.exists():
        shutil.rmtree(EASY)
    for name in EASY_NAMES:
        src = SUITE / name
        dst = EASY / name
        shutil.copytree(src, dst)


def main():
    if HARD.exists():
        shutil.rmtree(HARD)
    h01(); h02(); h03(); h04(); h05(); h06(); h07(); h08(); h09(); h10()
    easy()
    print(f"wrote tasks under {ROOT / 'tasks'}")


if __name__ == "__main__":
    main()
