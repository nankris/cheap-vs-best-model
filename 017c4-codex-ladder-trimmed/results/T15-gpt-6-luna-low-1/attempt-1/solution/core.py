def solve(rows):
    """Return the sorted union of closed integer intervals in *rows*."""
    intervals = []
    for row in rows:
        left, right = row
        if left > right:
            left, right = right, left
        intervals.append((left, right))

    intervals.sort()
    merged = []
    for left, right in intervals:
        if merged and left <= merged[-1][1] + 1:
            if right > merged[-1][1]:
                merged[-1][1] = right
        else:
            merged.append([left, right])
    return merged
