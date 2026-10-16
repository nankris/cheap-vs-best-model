from copy import deepcopy


def solve(rows):
    """Select the latest version of each key, with later rows winning ties."""
    latest = {}
    for key, version, value in rows:
        if key not in latest or version >= latest[key][0]:
            latest[key] = (version, value)
    return deepcopy([
        [key, latest[key][1]]
        for key in sorted(latest)
        if latest[key][1] is not None
    ])
