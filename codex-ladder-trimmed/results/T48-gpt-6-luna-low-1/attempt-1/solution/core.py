from heapq import heappop, heappush


def solve(rows):
    """Return the minimum directed path cost described by ``rows``.

    The final row contains the source and target; preceding rows are weighted
    directed edges. Build a new adjacency map so caller-owned rows are untouched.
    """
    if not rows:
        raise ValueError("rows must include a final [source, target] row")

    *edges, query = rows
    source, target = query
    if source == target:
        return 0

    adjacency = {}
    for start, end, weight in edges:
        adjacency.setdefault(start, []).append((end, weight))

    distances = {source: 0}
    queue = [(0, source)]
    while queue:
        cost, node = heappop(queue)
        if cost != distances.get(node):
            continue
        if node == target:
            return cost
        for neighbor, weight in adjacency.get(node, ()):
            candidate = cost + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heappush(queue, (candidate, neighbor))
    return None
