from bisect import bisect_right


def solve(rows):
    jobs = sorted(rows, key=lambda row: row[1])
    ends = [row[1] for row in jobs]
    # best[i] is the maximum reward using the first i jobs by end time.
    best = [0]
    for i, (start, end, reward) in enumerate(jobs):
        compatible_count = bisect_right(ends, start, 0, i)
        best.append(max(best[-1], best[compatible_count] + reward))
    return best[-1]
