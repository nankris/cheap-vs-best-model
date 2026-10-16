def solve(rows):
    """Return the minimum spanning forest weight without modifying rows."""
    node_names, edges = rows
    parent = {node: node for node in node_names}
    size = {node: 1 for node in node_names}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    total = 0
    for u, v, weight in sorted(edges, key=lambda edge: edge[2]):
        if u == v:
            continue
        root_u, root_v = find(u), find(v)
        if root_u == root_v:
            continue
        if size[root_u] < size[root_v]:
            root_u, root_v = root_v, root_u
        parent[root_v] = root_u
        size[root_u] += size[root_v]
        total += weight
    return total
