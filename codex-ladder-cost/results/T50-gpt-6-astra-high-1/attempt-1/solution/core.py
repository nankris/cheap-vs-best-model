"""Maximum reward from mutually nonoverlapping jobs."""

from bisect import bisect_right


def solve(rows):
    """Return the best reward, allowing an empty selection of jobs.

    Sort a copy by finish time. For each job, binary search for the last
    compatible prefix and choose between taking the job and skipping it.
    """
    jobs = sorted(rows, key=lambda job: job[1])
    ends = [job[1] for job in jobs]
    best = [0]
    for index, (start, _end, reward) in enumerate(jobs):
        compatible_count = bisect_right(ends, start, 0, index)
        best.append(max(best[-1], best[compatible_count] + reward))
    return best[-1]
