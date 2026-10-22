def solve(rows):
    """Return the strongly connected components in a sequence of edges."""
    adjacency = {}
    for source, target in rows:
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set())

    # Iterative Kosaraju avoids recursion limits on long input graphs.
    visited = set()
    finish_order = []
    for start in adjacency:
        if start in visited:
            continue
        visited.add(start)
        stack = [(start, iter(adjacency[start]))]
        while stack:
            node, neighbors = stack[-1]
            try:
                neighbor = next(neighbors)
            except StopIteration:
                finish_order.append(node)
                stack.pop()
                continue
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append((neighbor, iter(adjacency[neighbor])))

    reverse = {node: set() for node in adjacency}
    for source, neighbors in adjacency.items():
        for target in neighbors:
            reverse[target].add(source)

    assigned = set()
    components = []
    for start in reversed(finish_order):
        if start in assigned:
            continue
        component = []
        stack = [start]
        assigned.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in reverse[node]:
                if neighbor not in assigned:
                    assigned.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))

    return sorted(components)
