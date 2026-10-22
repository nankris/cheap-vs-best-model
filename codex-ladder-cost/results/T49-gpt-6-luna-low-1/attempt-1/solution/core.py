"""Core row resolution algorithm."""


def solve(rows):
    """Resolve versioned rows into sorted ``[key, value]`` pairs.

    For each key, the greatest version wins; rows encountered later win ties.
    A winning null value deletes the key.
    """
    latest = {}
    for key, version, value in rows:
        previous = latest.get(key)
        if previous is None or version >= previous[0]:
            latest[key] = (version, value)

    return [[key, value] for key, (version, value) in sorted(latest.items())
            if value is not None]
