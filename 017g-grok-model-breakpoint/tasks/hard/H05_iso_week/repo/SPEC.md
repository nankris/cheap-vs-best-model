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
