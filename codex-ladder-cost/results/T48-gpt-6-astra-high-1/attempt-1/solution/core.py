"""Minimum path costs for directed graphs with nonnegative edge weights."""

from heapq import heappop, heappush
from itertools import count


def solve(rows):
    source, target = rows[-1]
    if source == target:
        return 0

    adjacency = {}
    for u, v, weight in rows[:-1]:
        adjacency.setdefault(u, []).append((v, weight))

    distances = {source: 0}
    # A unique tie breaker keeps heap comparisons independent of vertex labels.
    sequence = count()
    pending = [(0, next(sequence), source)]
    while pending:
        distance, _, vertex = heappop(pending)
        if distance != distances[vertex]:
            continue
        if vertex == target:
            return distance
        for neighbor, weight in adjacency.get(vertex, ()):
            candidate = distance + weight
            previous = distances.get(neighbor)
            if previous is None or candidate < previous:
                distances[neighbor] = candidate
                heappush(pending, (candidate, next(sequence), neighbor))
    return None
