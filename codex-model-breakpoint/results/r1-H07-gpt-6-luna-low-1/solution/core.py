def solve(rows):
    """Return sorted connected components for an iterable of string edges."""
    parent = {}

    def find(node):
        # Every endpoint is registered before find is called.
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != node:
            next_node = parent[node]
            parent[node] = root
            node = next_node
        return root

    for edge in rows:
        left, right = edge
        parent.setdefault(left, left)
        parent.setdefault(right, right)
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    components = {}
    for node in parent:
        components.setdefault(find(node), []).append(node)

    result = [sorted(component) for component in components.values()]
    result.sort()
    return result
