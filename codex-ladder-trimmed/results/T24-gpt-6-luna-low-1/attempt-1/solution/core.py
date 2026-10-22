from copy import deepcopy


def solve(rows):
    """Apply a sequence of state operations and return sorted key/value rows."""
    state = {}
    stack = []

    for row in rows:
        op = row[0]
        if op == "set":
            state[row[1]] = deepcopy(row[2])
        elif op == "delete":
            state.pop(row[1], None)
        elif op == "begin":
            stack.append(deepcopy(state))
        elif op == "commit":
            if stack:
                stack.pop()
        elif op == "rollback":
            if stack:
                state = stack.pop()

    return [[key, deepcopy(state[key])] for key in sorted(state)]
