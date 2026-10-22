from copy import deepcopy


def solve(rows):
    """Apply the legacy row operations and return sorted final state rows."""
    state = {}
    snapshots = []

    for row in rows:
        op = row[0]
        if op == "set":
            key, value = row[1], row[2]
            state[key] = deepcopy(value)
        elif op == "delete":
            state.pop(row[1], None)
        elif op == "begin":
            snapshots.append(deepcopy(state))
        elif op == "commit":
            if snapshots:
                snapshots.pop()
        elif op == "rollback":
            if snapshots:
                state = snapshots.pop()

    return [[key, deepcopy(state[key])] for key in sorted(state)]
