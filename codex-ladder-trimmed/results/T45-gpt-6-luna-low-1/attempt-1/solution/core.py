def solve(rows):
    """Return the normalized union of closed integer intervals."""
    intervals = []
    for start, end in rows:
        if start > end:
            start, end = end, start
        intervals.append((start, end))

    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end

    return [tuple(interval) for interval in merged]
