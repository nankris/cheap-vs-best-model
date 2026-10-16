"""Shortest paths in directed graphs with nonnegative edge weights."""

from heapq import heappop, heappush
from itertools import count


def solve(rows):
    source, target = rows[-1]
    if source == target:
        return 0

    edges = {}
    for u, v, weight in rows[:-1]:
        edges.setdefault(u, []).append((v, weight))

    distances = {source: 0}
    sequence = count()
    # A sequence number keeps heap ties from comparing vertex labels.
    pending = [(0, next(sequence), source)]
    while pending:
        cost, _, vertex = heappop(pending)
        if cost != distances[vertex]:
            continue
        if vertex == target:
            return cost
        for neighbor, weight in edges.get(vertex, ()):
            candidate = cost + weight
            if neighbor not in distances or candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heappush(pending, (candidate, next(sequence), neighbor))
    return None
