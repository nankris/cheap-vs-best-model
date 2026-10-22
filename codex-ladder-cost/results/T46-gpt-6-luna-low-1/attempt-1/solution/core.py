"""Algorithms for dependency ordering."""

from heapq import heappop, heappush


def solve(rows):
    """Return the lexicographically smallest topological ordering.

    Nodes are the string endpoints mentioned in ``rows``.  Duplicate edges
    have no effect.  ``None`` signals that the graph contains a cycle.
    """
    successors = {}
    indegree = {}

    for before, after in rows:
        if before not in successors:
            successors[before] = set()
            indegree[before] = 0
        if after not in successors:
            successors[after] = set()
            indegree[after] = 0
        if after not in successors[before]:
            successors[before].add(after)
            indegree[after] += 1

    ready = []
    for node, degree in indegree.items():
        if degree == 0:
            heappush(ready, node)

    ordered = []
    while ready:
        node = heappop(ready)
        ordered.append(node)
        for after in successors[node]:
            indegree[after] -= 1
            if indegree[after] == 0:
                heappush(ready, after)

    return ordered if len(ordered) == len(indegree) else None
