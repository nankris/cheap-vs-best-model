def solve(rows):
    """Return the lexicographically ordered connected components in rows."""
    neighbors = {}
    for edge in rows:
        left, right = edge
        neighbors.setdefault(left, set()).add(right)
        neighbors.setdefault(right, set()).add(left)

    components = []
    unseen = set(neighbors)
    while unseen:
        start = min(unseen)
        stack = [start]
        unseen.remove(start)
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in neighbors[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))

    return sorted(components)
