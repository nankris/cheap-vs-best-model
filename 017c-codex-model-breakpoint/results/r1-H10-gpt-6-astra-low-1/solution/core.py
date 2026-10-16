from copy import deepcopy


def solve(rows):
    state = {}
    snapshots = []
    for row in rows:
        operation = row[0]
        if operation == "set":
            state[row[1]] = deepcopy(row[2])
        elif operation == "delete":
            state.pop(row[1], None)
        elif operation == "begin":
            snapshots.append(deepcopy(state))
        elif operation == "commit":
            if snapshots:
                snapshots.pop()
        elif operation == "rollback":
            if snapshots:
                state = snapshots.pop()
    return [[key, state[key]] for key in sorted(state)]
