import heapq


def solve(rows):
    """Return the lexicographically smallest topological order, or None."""
    edges = set()
    nodes = set()
    for before, after in rows:
        nodes.add(before)
        nodes.add(after)
        edges.add((before, after))

    outgoing = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    for before, after in edges:
        outgoing[before].add(after)
        indegree[after] += 1

    ready = [node for node in nodes if indegree[node] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for successor in outgoing[node]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)

    return order if len(order) == len(nodes) else None
