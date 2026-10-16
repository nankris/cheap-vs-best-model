def solve(rows):
    winners = {}

    for key, version, value in rows:
        current = winners.get(key)
        if current is None or version >= current[0]:
            winners[key] = (version, value)

    return [[key, winner[1]] for key, winner in sorted(winners.items()) if winner[1] is not None]
