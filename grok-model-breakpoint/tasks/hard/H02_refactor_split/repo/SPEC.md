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
