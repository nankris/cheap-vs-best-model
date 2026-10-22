from bisect import bisect_right


def solve(rows):
    jobs = sorted(rows, key=lambda row: row[1])
    ends = [end for _, end, _ in jobs]
    # best[i] is the maximum reward using the first i jobs by end time.
    best = [0]
    for i, (start, _, reward) in enumerate(jobs):
        compatible = bisect_right(ends, start, 0, i)
        best.append(max(best[-1], best[compatible] + reward))
    return best[-1]
