def solve(rows):
    """Return the lexicographically ordered connected components of rows."""
    parent = {}

    def find(node):
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != node:
            next_node = parent[node]
            parent[node] = root
            node = next_node
        return root

    for left, right in rows:
        if left not in parent:
            parent[left] = left
        if right not in parent:
            parent[right] = right
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
