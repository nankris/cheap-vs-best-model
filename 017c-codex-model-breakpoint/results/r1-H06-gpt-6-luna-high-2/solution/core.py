from bisect import bisect_right


def solve(rows):
    """Return the greatest reward from a set of nonoverlapping jobs.

    Jobs are ``(start, end, reward)`` triples. Sorting by end time lets the
    dynamic program consider every possible last job, while binary search
    finds the best compatible prefix in logarithmic time.
    """
    jobs = sorted(rows, key=lambda job: job[1])
    ends = [job[1] for job in jobs]
    best = [0] * (len(jobs) + 1)

    for i, (start, end, reward) in enumerate(jobs):
        # Only jobs before i are eligible. bisect_right permits a prior job
        # whose end equals this job's start.
        compatible_count = bisect_right(ends, start, 0, i)
        take = best[compatible_count] + reward
        best[i + 1] = max(best[i], take)

    return best[-1]
