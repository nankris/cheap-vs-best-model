def solve(rows):
    """Return sorted connected components without changing the input edges."""
    adjacency = {}
    for left, right in rows:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    visited = set()
    components = []
    for node in adjacency:
        if node in visited:
            continue
        visited.add(node)
        pending = [node]
        component = []
        while pending:
            current = pending.pop()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))
    return sorted(components)
