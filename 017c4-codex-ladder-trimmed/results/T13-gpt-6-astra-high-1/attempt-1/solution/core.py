def solve(rows):
    """Return sorted strongly connected components without modifying rows."""
    graph = {}
    reverse = {}
    for source, target in rows:
        graph.setdefault(source, set()).add(target)
        graph.setdefault(target, set())
        reverse.setdefault(target, set()).add(source)
        reverse.setdefault(source, set())

    # Iterative Kosaraju traversal avoids recursion limits on long paths.
    visited = set()
    finished = []
    for start in graph:
        if start in visited:
            continue
        visited.add(start)
        stack = [(start, iter(graph[start]))]
        while stack:
            node, neighbors = stack[-1]
            neighbor = next(neighbors, None)
            if neighbor is None:
                finished.append(node)
                stack.pop()
            elif neighbor not in visited:
                visited.add(neighbor)
                stack.append((neighbor, iter(graph[neighbor])))

    visited.clear()
    components = []
    for start in reversed(finished):
        if start in visited:
            continue
        visited.add(start)
        pending = [start]
        component = []
        while pending:
            node = pending.pop()
            component.append(node)
            for neighbor in reverse[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
        components.append(sorted(component))
    return sorted(components)
