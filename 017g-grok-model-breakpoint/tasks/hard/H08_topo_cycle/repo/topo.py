class CycleError(Exception):
    pass

def topo_sort(nodes, edges):
    adj = {}
    indeg = {}
    for before, after in edges:
        adj.setdefault(before, []).append(after)
        indeg.setdefault(before, 0)
        indeg[after] = indeg.get(after, 0) + 1
    queue = [name for name, degree in indeg.items() if degree == 0]
    order = []
    while queue:
        name = queue.pop(0)
        order.append(name)
        for nxt in adj.get(name, []):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return order
