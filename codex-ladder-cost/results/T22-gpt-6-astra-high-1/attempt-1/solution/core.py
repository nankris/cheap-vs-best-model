"""Compute the length covered by an odd number of intervals."""


def solve(rows):
    # Only endpoints with odd multiplicity change coverage parity.
    boundaries = set()
    for start, end in rows:
        if start < end:
            boundaries.symmetric_difference_update((start, end))
    points = sorted(boundaries)
    return sum(points[i + 1] - points[i] for i in range(0, len(points), 2))
