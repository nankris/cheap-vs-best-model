"""Apply row operations, including nested transactions."""

from copy import deepcopy


def solve(rows):
    """Return the final sorted rows after applying the operations."""
    state = {}
    snapshots = []

    for operation in rows:
        if not isinstance(operation, list) or not operation:
            raise ValueError("invalid operation")

        kind = operation[0]
        if kind == "set" and len(operation) == 3:
            _, key, value = operation
            state[key] = deepcopy(value)
        elif kind == "delete" and len(operation) == 2:
            _, key = operation
            state.pop(key, None)
        elif kind == "begin" and len(operation) == 1:
            snapshots.append(deepcopy(state))
        elif kind == "commit" and len(operation) == 1:
            if snapshots:
                snapshots.pop()
        elif kind == "rollback" and len(operation) == 1:
            if snapshots:
                state = snapshots.pop()
        else:
            raise ValueError("invalid operation")

    return [[key, deepcopy(state[key])] for key in sorted(state)]
