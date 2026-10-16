from bisect import bisect_right


def solve(rows):
    jobs = sorted(rows, key=lambda row: row[1])
    ends = [end for _, end, _ in jobs]
    best = [0]
    for index, (start, _, reward) in enumerate(jobs):
        # Only earlier jobs ending at or before this start are compatible.
        compatible = bisect_right(ends, start, 0, index)
        best.append(max(best[-1], best[compatible] + reward))
    return best[-1]
