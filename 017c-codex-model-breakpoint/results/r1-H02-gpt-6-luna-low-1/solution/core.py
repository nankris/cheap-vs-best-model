import heapq


def solve(rows):
    """Return the lexicographically smallest topological ordering, or None."""
    outgoing = {}
    indegree = {}

    for before, after in rows:
        outgoing.setdefault(before, set())
        outgoing.setdefault(after, set())
        indegree.setdefault(before, 0)
        indegree.setdefault(after, 0)
        if after not in outgoing[before]:
            outgoing[before].add(after)
            indegree[after] += 1

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordering = []

    while ready:
        node = heapq.heappop(ready)
        ordering.append(node)
        for neighbor in outgoing[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heapq.heappush(ready, neighbor)

    if len(ordering) != len(indegree):
        return None
    return ordering
