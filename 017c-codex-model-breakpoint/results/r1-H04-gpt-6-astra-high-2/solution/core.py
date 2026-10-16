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
    sequence = count()
    pending = [(0, next(sequence), source)]
    while pending:
        cost, _, node = heappop(pending)
        if cost != distances[node]:
            continue
        if node == target:
            return cost
        for neighbor, weight in adjacency.get(node, ()):
            candidate = cost + weight
            if neighbor not in distances or candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heappush(pending, (candidate, next(sequence), neighbor))

    return None
