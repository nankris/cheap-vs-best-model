"""Shortest-path algorithm used by the journal service."""

import heapq


def solve(rows):
    """Return the minimum directed path cost for the final source/target row."""
    edges = rows[:-1]
    source, target = rows[-1]
    if source == target:
        return 0

    adjacency = {}
    for u, v, weight in edges:
        adjacency.setdefault(u, []).append((v, weight))

    distances = {source: 0}
    queue = [(0, source)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distances.get(node):
            continue
        if node == target:
            return cost
        for neighbor, weight in adjacency.get(node, ()):
            candidate = cost + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return None
