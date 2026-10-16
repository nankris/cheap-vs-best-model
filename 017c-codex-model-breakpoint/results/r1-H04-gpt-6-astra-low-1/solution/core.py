from heapq import heappop, heappush
from itertools import count


def solve(rows):
    source, target = rows[-1]
    if source == target:
        return 0

    adjacency = {}
    for start, end, weight in rows[:-1]:
        adjacency.setdefault(start, []).append((end, weight))

    distances = {source: 0}
    # A sequence number breaks ties without comparing vertex labels.
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
