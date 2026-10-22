def solve(rows):
    """Return the union of closed integer intervals, merging adjacency."""
    intervals = sorted((min(start, end), max(start, end)) for start, end in rows)
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return merged
