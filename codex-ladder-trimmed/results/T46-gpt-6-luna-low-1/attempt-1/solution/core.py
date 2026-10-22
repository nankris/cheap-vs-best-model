from heapq import heappop, heappush


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

    ready = []
    for node, degree in indegree.items():
        if degree == 0:
            heappush(ready, node)

    ordering = []
    while ready:
        node = heappop(ready)
        ordering.append(node)
        for neighbor in adjacency[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heappush(ready, neighbor)

    if len(ordering) != len(indegree):
        return None
    return ordering
