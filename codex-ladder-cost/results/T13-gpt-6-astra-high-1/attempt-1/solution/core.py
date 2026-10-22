def solve(rows):
    """Return sorted strongly connected components of directed string edges."""
    graph = {}
    reverse = {}
    for source, target in rows:
        graph.setdefault(source, set()).add(target)
        graph.setdefault(target, set())
        reverse.setdefault(target, set()).add(source)
        reverse.setdefault(source, set())

    # Iterative DFS records finishing order without relying on recursion depth.
    visited = set()
    finished = []
    for node in graph:
        if node in visited:
            continue
        visited.add(node)
        stack = [(node, iter(graph[node]))]
        while stack:
            current, neighbors = stack[-1]
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append((neighbor, iter(graph[neighbor])))
                    break
            else:
                stack.pop()
                finished.append(current)

    # Reverse edges separate components when visited in reverse finish order.
    visited = set()
    components = []
    for node in reversed(finished):
        if node in visited:
            continue
        visited.add(node)
        pending = [node]
        component = []
        while pending:
            current = pending.pop()
            component.append(current)
            for neighbor in reverse[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))

    return sorted(components)
