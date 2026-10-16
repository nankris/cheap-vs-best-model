def solve(rows):
    """Return the sorted union of closed integer intervals in *rows*."""
    intervals = []
    for start, end in rows:
        if start > end:
            start, end = end, start
        intervals.append((start, end))

    intervals.sort(key=lambda interval: interval[0])
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return [tuple(interval) for interval in merged]
