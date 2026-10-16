def solve(rows):
    """Return the length covered by an odd number of valid intervals."""
    toggles = {}
    for row in rows:
        start, end = row
        if start >= end:
            continue
        toggles[start] = not toggles.get(start, False)
        toggles[end] = not toggles.get(end, False)

    total = 0
    odd = False
    previous = None
    for point in sorted(toggles):
        if odd:
            total += point - previous
        if toggles[point]:
            odd = not odd
        previous = point
    return total
