"""Maximum reward from a set of nonoverlapping jobs."""

from bisect import bisect_right


def solve(rows):
    jobs = sorted(rows, key=lambda job: job[1])
    ends = [job[1] for job in jobs]
    best = [0]
    for index, (start, end, reward) in enumerate(jobs):
        # Only earlier jobs whose end is at or before start can precede us.
        compatible = bisect_right(ends, start, 0, index)
        best.append(max(best[-1], best[compatible] + reward))
    return best[-1]
