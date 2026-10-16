"""Lexicographically smallest topological ordering of directed edges."""

import heapq


def solve(rows):
    successors = {}
    indegree = {}
    for before, after in rows:
        successors.setdefault(before, set())
        successors.setdefault(after, set())
        indegree.setdefault(before, 0)
        indegree.setdefault(after, 0)
        if after not in successors[before]:
            successors[before].add(after)
            indegree[after] += 1

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        node = heapq.heappop(ready)
        ordered.append(node)
        for successor in successors[node]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)

    return ordered if len(ordered) == len(indegree) else None
