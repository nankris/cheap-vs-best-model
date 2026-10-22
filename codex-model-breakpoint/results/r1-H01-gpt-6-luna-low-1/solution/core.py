def solve(rows):
    intervals = []
    for row in rows:
        start, end = row
        if start > end:
            start, end = end, start
        intervals.append((start, end))

    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))

    return [list(interval) for interval in merged]
