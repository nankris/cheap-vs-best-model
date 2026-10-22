import heapq


def solve(rows):
    """Return the lexicographically smallest topological ordering, or None."""
    nodes = set()
    outgoing = {}
    indegree = {}

    for before, after in rows:
        nodes.add(before)
        nodes.add(after)
        neighbors = outgoing.setdefault(before, set())
        if after not in neighbors:
            neighbors.add(after)
            indegree[after] = indegree.get(after, 0) + 1
        indegree.setdefault(before, 0)

    ready = [node for node in nodes if indegree.get(node, 0) == 0]
    heapq.heapify(ready)
    ordering = []

    while ready:
        node = heapq.heappop(ready)
        ordering.append(node)
        for neighbor in outgoing.get(node, ()):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heapq.heappush(ready, neighbor)

    if len(ordering) != len(nodes):
        return None
    return ordering
