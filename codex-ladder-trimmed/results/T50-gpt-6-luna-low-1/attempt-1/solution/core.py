from bisect import bisect_right


def solve(rows):
    """Return the greatest reward obtainable from nonoverlapping jobs."""
    jobs = sorted((start, end, reward) for start, end, reward in rows)
    ends = [job[1] for job in jobs]

    # dp[i] is the best reward using the first i jobs in start/end order.
    dp = [0] * (len(jobs) + 1)
    for index, (start, end, reward) in enumerate(jobs):
        # All jobs ending at or before this start may precede this job.
        compatible = bisect_right(ends, start, 0, index)
        take = dp[compatible] + reward
        dp[index + 1] = max(dp[index], take)
    return dp[-1]
