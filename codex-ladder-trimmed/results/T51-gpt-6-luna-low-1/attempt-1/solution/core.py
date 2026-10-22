def solve(rows):
    """Return the sorted connected components of an undirected edge list."""
    adjacency = {}
    for left, right in rows:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    components = []
    unseen = set(adjacency)
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        stack = [start]
        component = []

        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)

        components.append(sorted(component))

    return sorted(components)
