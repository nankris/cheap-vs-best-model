def solve(rows):
    neighbors = {}
    for left, right in rows:
        neighbors.setdefault(left, set()).add(right)
        neighbors.setdefault(right, set()).add(left)

    components = []
    visited = set()
    for node in neighbors:
        if node in visited:
            continue
        visited.add(node)
        pending = [node]
        component = []
        while pending:
            current = pending.pop()
            component.append(current)
            for neighbor in neighbors[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))
    return sorted(components)
