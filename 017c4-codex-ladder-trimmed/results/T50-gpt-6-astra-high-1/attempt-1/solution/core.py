"""Maximum-reward scheduling of nonoverlapping jobs."""

from bisect import bisect_right


def solve(rows):
    """Return the best reward, without modifying the input jobs."""
    jobs = sorted(rows, key=lambda row: row[1])
    ends = [job[1] for job in jobs]
    # best[i] is the optimum using only the first i jobs by end time.
    best = [0]
    for i, (start, _end, reward) in enumerate(jobs):
        compatible = bisect_right(ends, start, 0, i)
        best.append(max(best[-1], best[compatible] + reward))
    return best[-1]
