"""Connected components for undirected string edges."""


def solve(rows):
    neighbors = {}
    for left, right in rows:
        neighbors.setdefault(left, set()).add(right)
        neighbors.setdefault(right, set()).add(left)

    seen = set()
    components = []
    for node in neighbors:
        if node in seen:
            continue
        seen.add(node)
        pending = [node]
        component = []
        while pending:
            current = pending.pop()
            component.append(current)
            for neighbor in neighbors[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))
    return sorted(components)
