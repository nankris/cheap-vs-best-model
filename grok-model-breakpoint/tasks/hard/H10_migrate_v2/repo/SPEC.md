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
