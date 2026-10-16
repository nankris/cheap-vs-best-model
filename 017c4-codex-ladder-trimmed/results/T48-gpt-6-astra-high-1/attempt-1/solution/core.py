"""Minimum costs in a directed graph with nonnegative edge weights."""

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
    # A unique tie breaker avoids comparing vertex labels in the heap.
    sequence = count()
    pending = [(0, next(sequence), source)]
    while pending:
        cost, _, vertex = heappop(pending)
        if cost != distances[vertex]:
            continue
        if vertex == target:
            return cost
        for neighbor, weight in adjacency.get(vertex, ()):
            candidate = cost + weight
            if neighbor not in distances or candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heappush(pending, (candidate, next(sequence), neighbor))
    return None
