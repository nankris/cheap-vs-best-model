def solve(rows):
    state = {}
    snapshots = []

    for row in rows:
        operation = row[0]

        if operation == "set":
            _, key, value = row
            state[key] = value
        elif operation == "delete":
            _, key = row
            state.pop(key, None)
        elif operation == "begin":
            snapshots.append(state.copy())
        elif operation == "commit":
            if snapshots:
                snapshots.pop()
        elif operation == "rollback":
            if snapshots:
                state = snapshots.pop()

    return [[key, state[key]] for key in sorted(state)]
