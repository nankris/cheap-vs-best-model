import heapq


def solve(rows):
    """Return the lexicographically smallest topological ordering, or None."""
    outgoing = {}
    indegree = {}

    for before, after in rows:
        if before not in indegree:
            indegree[before] = 0
            outgoing[before] = set()
        if after not in indegree:
            indegree[after] = 0
            outgoing[after] = set()
        if after not in outgoing[before]:
            outgoing[before].add(after)
            indegree[after] += 1

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        node = heapq.heappop(ready)
        ordered.append(node)
        for neighbor in outgoing[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heapq.heappush(ready, neighbor)

    return ordered if len(ordered) == len(indegree) else None
