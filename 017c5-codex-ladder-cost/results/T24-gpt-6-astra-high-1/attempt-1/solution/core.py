"""Evaluate rows of nested transactional state operations."""

from copy import deepcopy


def solve(rows):
    state = {}
    snapshots = []
    for row in rows:
        op = row[0]
        if op == "set":
            state[row[1]] = deepcopy(row[2])
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
    return deepcopy([[key, state[key]] for key in sorted(state)])
