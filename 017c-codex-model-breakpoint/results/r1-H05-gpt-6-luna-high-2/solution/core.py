def solve(rows):
    winners = {}

    for key, version, value in rows:
        current = winners.get(key)
        # Replacing on equal versions makes the last row win a tie.
        if current is None or version >= current[0]:
            winners[key] = (version, value)

    return [
        [key, value]
        for key, (version, value) in sorted(winners.items())
        if value is not None
    ]
