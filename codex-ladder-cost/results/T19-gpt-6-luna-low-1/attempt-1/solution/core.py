def solve(rows):
    """Select the latest row for every key and omit keys deleted by null."""
    latest = {}
    for key, version, value in rows:
        previous = latest.get(key)
        if previous is None or version >= previous[0]:
            latest[key] = (version, value)
    return [[key, value] for key, (version, value) in sorted(latest.items()) if value is not None]
