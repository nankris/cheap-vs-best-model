import heapq

class CycleError(Exception):
    pass

def topo_sort(nodes, edges):
    node_list = list(nodes)
    if len(set(node_list)) != len(node_list):
        raise ValueError("duplicate node")
    adj = {name: [] for name in node_list}
    indeg = {name: 0 for name in node_list}
    seen = set()
    for before, after in edges:
        if before not in indeg or after not in indeg:
            raise ValueError("unknown node")
        if (before, after) in seen:
            continue
        seen.add((before, after))
        adj[before].append(after)
        indeg[after] += 1
    ready = [name for name in node_list if indeg[name] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        name = heapq.heappop(ready)
        order.append(name)
        for nxt in adj[name]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(ready, nxt)
    if len(order) != len(node_list):
        raise CycleError("cycle")
    return order
