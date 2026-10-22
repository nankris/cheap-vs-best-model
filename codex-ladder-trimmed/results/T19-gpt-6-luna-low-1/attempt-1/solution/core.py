def solve(rows):
    """Select the latest version for each key, with later rows winning ties."""
    latest = {}
    for key, version, value in rows:
        previous = latest.get(key)
        if previous is None or version >= previous[0]:
            latest[key] = (version, value)
    return [[key, value] for key, (version, value) in sorted(latest.items()) if value is not None]
