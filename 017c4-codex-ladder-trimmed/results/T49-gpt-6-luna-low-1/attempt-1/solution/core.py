def solve(rows):
    """Resolve versioned rows, with the last row winning on version ties."""
    latest = {}
    for key, version, value in rows:
        previous = latest.get(key)
        if previous is None or version >= previous[0]:
            latest[key] = (version, value)

    return [[key, value] for key, (version, value) in sorted(latest.items()) if value is not None]
