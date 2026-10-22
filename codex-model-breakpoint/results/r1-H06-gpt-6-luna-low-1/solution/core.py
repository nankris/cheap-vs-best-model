from bisect import bisect_right


def solve(rows):
    """Return the maximum reward among a set of nonoverlapping jobs."""
    jobs = sorted(rows, key=lambda job: job[1])
    ends = [job[1] for job in jobs]
    best = [0] * (len(jobs) + 1)

    for i, (start, end, reward) in enumerate(jobs, start=1):
        # bisect_right permits a preceding job whose end equals this start.
        compatible_count = bisect_right(ends, start, 0, i - 1)
        best[i] = max(best[i - 1], best[compatible_count] + reward)

    return best[-1]
