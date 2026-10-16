"""Shortest-path algorithm used by the journal's ``put`` command."""

from heapq import heappop, heappush
from itertools import count


def solve(rows):
    """Return the minimum directed path cost for the final source/target row.

    All rows before the final row are weighted edges ``[u, v, weight]``;
    the last row is ``[source, target]``. Inputs are guaranteed valid.
    """
    edges = rows[:-1]
    source, target = rows[-1]
    if source == target:
        return 0

    graph = {}
    for u, v, weight in edges:
        graph.setdefault(u, []).append((v, weight))

    distances = {source: 0}
    sequence = count()
    queue = [(0, next(sequence), source)]
    while queue:
        cost, _, node = heappop(queue)
        if cost != distances.get(node):
            continue
        if node == target:
            return cost
        for neighbor, weight in graph.get(node, ()):
            candidate = cost + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heappush(queue, (candidate, next(sequence), neighbor))
    return None
