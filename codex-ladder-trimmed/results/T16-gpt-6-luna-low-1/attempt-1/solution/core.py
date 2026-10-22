import heapq


def solve(rows):
    """Return the lexicographically smallest topological ordering, or None."""
    adjacency = {}
    indegree = {}

    for before, after in rows:
        if before not in adjacency:
            adjacency[before] = set()
            indegree[before] = 0
        if after not in adjacency:
            adjacency[after] = set()
            indegree[after] = 0
        if after not in adjacency[before]:
            adjacency[before].add(after)
            indegree[after] += 1

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordering = []
    while ready:
        node = heapq.heappop(ready)
        ordering.append(node)
        for successor in adjacency[node]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)

    return ordering if len(ordering) == len(indegree) else None
