from bisect import bisect_right


def solve(rows):
    """Return the greatest reward obtainable from compatible jobs."""
    jobs = sorted(rows, key=lambda job: job[1])
    ends = [job[1] for job in jobs]
    best = [0] * (len(jobs) + 1)

    for i, (start, end, reward) in enumerate(jobs, start=1):
        compatible = bisect_right(ends, start, 0, i - 1)
        best[i] = max(best[i - 1], best[compatible] + reward)

    return best[-1]
