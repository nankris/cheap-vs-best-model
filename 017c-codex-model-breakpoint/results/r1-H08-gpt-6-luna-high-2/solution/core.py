def solve(rows):
    """Return the integer length covered by an odd number of intervals."""
    events = {}
    for row in rows:
        start, end = row
        if start >= end:
            continue
        events[start] = events.get(start, 0) + 1
        events[end] = events.get(end, 0) + 1

    covered = 0
    odd = False
    previous = None
    for point in sorted(events):
        if odd:
            covered += point - previous
        if events[point] % 2:
            odd = not odd
        previous = point
    return covered
