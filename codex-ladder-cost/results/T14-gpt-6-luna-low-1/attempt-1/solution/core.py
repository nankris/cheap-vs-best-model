def solve(rows):
    """Return the minimum spanning forest weight for one graph input."""
    node_names, edges = rows
    # Node names are labels; map them to compact indices for union-find.
    indices = {name: index for index, name in enumerate(node_names)}
    parent = list(range(len(node_names)))
    rank = [0] * len(parent)

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            return False
        if rank[left_root] < rank[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        if rank[left_root] == rank[right_root]:
            rank[left_root] += 1
        return True

    total = 0
    for left, right, weight in sorted(edges, key=lambda edge: edge[2]):
        if left == right:
            continue
        if union(indices[left], indices[right]):
            total += weight
    return total
