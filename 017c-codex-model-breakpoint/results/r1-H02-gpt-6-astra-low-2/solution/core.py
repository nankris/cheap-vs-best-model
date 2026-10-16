import heapq


def solve(rows):
    successors = {}
    indegrees = {}
    for before, after in rows:
        successors.setdefault(before, set())
        successors.setdefault(after, set())
        indegrees.setdefault(before, 0)
        indegrees.setdefault(after, 0)
        if after not in successors[before]:
            successors[before].add(after)
            indegrees[after] += 1

    ready = [node for node, degree in indegrees.items() if degree == 0]
    heapq.heapify(ready)
    ordering = []
    while ready:
        node = heapq.heappop(ready)
        ordering.append(node)
        for following in successors[node]:
            indegrees[following] -= 1
            if indegrees[following] == 0:
                heapq.heappush(ready, following)

    return ordering if len(ordering) == len(indegrees) else None
