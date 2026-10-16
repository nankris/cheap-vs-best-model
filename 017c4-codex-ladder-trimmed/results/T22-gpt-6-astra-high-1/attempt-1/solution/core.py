def solve(rows):
    """Return the length covered by an odd number of half-open intervals."""
    endpoints = set()
    for start, end in rows:
        if start >= end:
            continue
        for point in (start, end):
            if point in endpoints:
                endpoints.remove(point)
            else:
                endpoints.add(point)

    points = sorted(endpoints)
    return sum(points[i + 1] - points[i] for i in range(0, len(points), 2))
