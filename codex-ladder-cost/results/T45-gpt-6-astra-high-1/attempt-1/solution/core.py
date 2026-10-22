def solve(rows):
    """Return the sorted union of closed integer intervals without mutating rows."""
    intervals = sorted((min(start, end), max(start, end)) for start, end in rows)
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
