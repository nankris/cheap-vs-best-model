def solve(rows):
    """Return each key's latest non-deleted value, sorted by key."""
    latest = {}
    for key, version, value in rows:
        if key not in latest or version >= latest[key][0]:
            latest[key] = (version, value)
    return [
        [key, latest[key][1]]
        for key in sorted(latest)
        if latest[key][1] is not None
    ]
