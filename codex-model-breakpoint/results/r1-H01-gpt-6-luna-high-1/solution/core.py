def solve(rows):
    """Return the sorted union of closed integer intervals.

    Reversed endpoints are normalized, and ranges that overlap or touch at
    consecutive integer values are merged.
    """
    intervals = sorted((min(start, end), max(start, end)) for start, end in rows)
    if not intervals:
        return []

    merged = []
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end + 1:
            current_end = max(current_end, end)
        else:
            merged.append([current_start, current_end])
            current_start, current_end = start, end
    merged.append([current_start, current_end])
    return merged
