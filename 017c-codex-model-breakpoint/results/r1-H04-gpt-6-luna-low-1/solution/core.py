import heapq


def solve(rows):
    """Return the minimum path cost described by edge rows and a final query."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected a nonempty list of edge rows and a query row")

    query = rows[-1]
    if not isinstance(query, list) or len(query) != 2:
        raise ValueError("final row must contain source and target")
    source, target = query
    if source == target:
        return 0

    graph = {}
    for edge in rows[:-1]:
        if not isinstance(edge, list) or len(edge) != 3:
            raise ValueError("edge rows must contain source, target, and weight")
        start, end, weight = edge
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 0:
            raise ValueError("edge weights must be nonnegative integers")
        graph.setdefault(start, []).append((end, weight))

    distances = {source: 0}
    pending = [(0, source)]
    while pending:
        cost, node = heapq.heappop(pending)
        if cost != distances.get(node):
            continue
        if node == target:
            return cost
        for neighbor, weight in graph.get(node, ()):
            candidate = cost + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heapq.heappush(pending, (candidate, neighbor))
    return None
