def solve(rows):
    # Build a fresh graph on every call; read only the caller's edge rows.
    adjacency = {}
    for edge in rows:
        left, right = edge
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    components = []
    visited = set()
    for node in adjacency:
        if node in visited:
            continue
        component = []
        stack = [node]
        visited.add(node)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))

    return sorted(components)
