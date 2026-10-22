from bisect import bisect_right


def solve(rows):
    """Return the maximum reward from a set of nonoverlapping jobs."""
    jobs = sorted(rows, key=lambda row: (row[1], row[0]))
    ends = [job[1] for job in jobs]
    best = [0] * (len(jobs) + 1)
    for i, (start, _end, reward) in enumerate(jobs, 1):
        compatible = bisect_right(ends, start, 0, i - 1)
        best[i] = max(best[i - 1], best[compatible] + reward)
    return best[-1]
