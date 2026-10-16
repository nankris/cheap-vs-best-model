import heapq


def solve(rows):
    """Return the minimum directed path cost described by rows.

    All rows before the last are weighted directed edges; the last row is the
    source and target pair. The input is only read and never modified.
    """
    edges = rows[:-1]
    source, target = rows[-1]

    if source == target:
        return 0

    graph = {}
    for start, end, weight in edges:
        graph.setdefault(start, []).append((end, weight))

    distances = {source: 0}
    queue = [(0, source)]

    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distances.get(node):
            continue
        if node == target:
            return cost
        for neighbor, weight in graph.get(node, ()):
            candidate = cost + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))

    return None
