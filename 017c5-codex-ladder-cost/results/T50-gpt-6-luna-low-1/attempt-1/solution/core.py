from bisect import bisect_right


def solve(rows):
    """Return the maximum reward obtainable from nonoverlapping jobs."""
    jobs = sorted((end, start, reward) for start, end, reward in rows)
    ends = [job[0] for job in jobs]

    # best[i] is the best reward using the first i jobs in end-time order.
    best = [0] * (len(jobs) + 1)
    for i, (end, start, reward) in enumerate(jobs, start=1):
        # bisect only among earlier jobs. An end equal to this start is valid.
        compatible_count = bisect_right(ends, start, 0, i - 1)
        best[i] = max(best[i - 1], best[compatible_count] + reward)
    return best[-1]
