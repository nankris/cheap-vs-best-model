# Config merge

`defaults.DEFAULTS` is the base config. `merge.deep_merge(base, override)` must:

- Merge nested dicts. An override key replaces only itself. Sibling keys stay.
- Replace lists and scalars. Lists are not concatenated.
- Treat `None` as delete. `{"debug": None}` removes `debug`. `{"db": {"name": None}}` removes only `db.name`. `{"db": None}` removes `db`.
- Return a deep copy. Mutating the result must not change `base` or `DEFAULTS`.

`loader.load(override)` merges `DEFAULTS` with `override` and rejects unknown top-level keys with `ValueError`. Known top-level keys are `service`, `debug`, `db`, `limits`, and `tags`. Nested keys inside `db` and `limits` may be new. `service`, when present, must be a string. `limits.max_conn`, when present, must be an int. A bad type raises `ValueError`.

The visible test only overrides `db.port`.
