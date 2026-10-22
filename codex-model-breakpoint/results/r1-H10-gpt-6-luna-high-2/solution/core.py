def solve(rows):
    """Apply a sequence of key/value operations with nested transactions."""
    state = {}
    snapshots = []

    for operation in rows:
        name = operation[0]

        if name == "set":
            _, key, value = operation
            state[key] = value
        elif name == "delete":
            _, key = operation
            state.pop(key, None)
        elif name == "begin":
            # The operations replace or remove top-level values, so copying
            # the mapping is enough to preserve the prior state. Values are
            # never modified in place.
            snapshots.append(state.copy())
        elif name == "commit":
            if snapshots:
                snapshots.pop()
        elif name == "rollback":
            if snapshots:
                state = snapshots.pop()

    return [[key, state[key]] for key in sorted(state)]
