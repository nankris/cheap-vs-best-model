def solve(rows):
    """Return the total weight of a minimum spanning forest.

    ``rows`` is a pair consisting of node names and undirected weighted edges.
    A disjoint-set structure gives Kruskal's algorithm linear auxiliary space.
    """
    node_names, edges = rows
    parent = {name: name for name in node_names}
    rank = {name: 0 for name in node_names}

    def find(node):
        root = node
        while parent[root] != root:
            root = parent[root]
        while node != root:
            next_node = parent[node]
            parent[node] = root
            node = next_node
        return root

    total = 0
    for u, v, weight in sorted(edges, key=lambda edge: edge[2]):
        if u == v:
            continue
        root_u = find(u)
        root_v = find(v)
        if root_u == root_v:
            continue
        total += weight
        if rank[root_u] < rank[root_v]:
            parent[root_u] = root_v
        elif rank[root_u] > rank[root_v]:
            parent[root_v] = root_u
        else:
            parent[root_v] = root_u
            rank[root_u] += 1
    return total
