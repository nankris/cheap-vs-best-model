def solve(rows):
    """Return sorted connected components without changing the input edges."""
    neighbors = {}
    for left, right in rows:
        neighbors.setdefault(left, set()).add(right)
        neighbors.setdefault(right, set()).add(left)

    unseen = set(neighbors)
    components = []
    while unseen:
        start = unseen.pop()
        pending = [start]
        component = []
        while pending:
            node = pending.pop()
            component.append(node)
            for neighbor in neighbors[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))

    return sorted(components)
