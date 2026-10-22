import heapq
from itertools import count


def solve(rows):
    """Return the minimum directed path cost, or None when unreachable."""
    if not rows:
        raise ValueError("at least a source/target row is required")

    source, target = rows[-1]
    if source == target:
        return 0

    graph = {}
    for row in rows[:-1]:
        start, end, weight = row
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 0:
            raise ValueError("edge weights must be nonnegative integers")
        graph.setdefault(start, []).append((end, weight))

    distances = {source: 0}
    sequence = count()
    pending = [(0, next(sequence), source)]

    while pending:
        cost, _, vertex = heapq.heappop(pending)
        if cost != distances.get(vertex):
            continue
        if vertex == target:
            return cost
        for neighbor, weight in graph.get(vertex, ()):
            candidate = cost + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heapq.heappush(pending, (candidate, next(sequence), neighbor))

    return None
