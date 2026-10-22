def solve(rows):
    """Return the sorted union of closed integer intervals.

    Adjacent integer intervals are merged as well as overlapping intervals.
    """
    if not rows:
        return []

    ordered = sorted((min(start, end), max(start, end)) for start, end in rows)
    merged = []
    current_start, current_end = ordered[0]

    for start, end in ordered[1:]:
        if start <= current_end + 1:
            current_end = max(current_end, end)
        else:
            merged.append([current_start, current_end])
            current_start, current_end = start, end

    merged.append([current_start, current_end])
    return merged
