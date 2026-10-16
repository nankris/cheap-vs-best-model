def solve(rows):
    """Return sorted connected components for an iterable of undirected edges."""
    parent = {}

    def find(node):
        # Every node, including a node seen only in a self-loop, is registered.
        if node not in parent:
            parent[node] = node
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != node:
            next_node = parent[node]
            parent[node] = root
            node = next_node
        return root

    for edge in rows:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("each edge must contain exactly two nodes")
        left, right = edge
        if not isinstance(left, str) or not isinstance(right, str):
            raise ValueError("edge nodes must be strings")
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            # Root choice does not affect output ordering; deterministic choice
            # keeps the internal structure stable as well.
            if left_root < right_root:
                parent[right_root] = left_root
            else:
                parent[left_root] = right_root

    components = {}
    for node in parent:
        components.setdefault(find(node), []).append(node)
    result = [sorted(component) for component in components.values()]
    return sorted(result)
