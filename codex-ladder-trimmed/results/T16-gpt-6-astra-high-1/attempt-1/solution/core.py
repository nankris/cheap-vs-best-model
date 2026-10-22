"""Lexicographically smallest topological ordering of a directed graph."""

import heapq


def solve(rows):
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
        for after in outgoing[node]:
            indegree[after] -= 1
            if indegree[after] == 0:
                heapq.heappush(ready, after)

    return ordering if len(ordering) == len(indegree) else None
