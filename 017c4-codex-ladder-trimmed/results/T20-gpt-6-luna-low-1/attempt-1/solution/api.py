import copy
import json

from service import compute


_MISSING = object()
_NO_EVENT = object()


def _valid_command(command):
    """Return the recognized operation, or None when the command is malformed."""
    if not isinstance(command, dict):
        return None

    if "id" in command and not isinstance(command["id"], str):
        return None

    op = command.get("op", _MISSING)
    requirements = {
        "put": ("key", "input"),
        "get": ("key",),
        "delete": ("key",),
        "expect": ("key", "value"),
        "begin": (),
        "commit": (),
        "rollback": (),
        "list": (),
    }
    if not isinstance(op, str) or op not in requirements:
        return None
    for field in requirements[op]:
        if field not in command:
            return None
    if "key" in requirements[op] and not isinstance(command["key"], str):
        return None
    return op


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _execute(op, command, state, stack):
    if op == "put":
        value = compute(command["input"]).value
        state[command["key"]] = copy.deepcopy(value)
        return {"ok": copy.deepcopy(value)}
    if op == "get":
        value = state.get(command["key"], _MISSING)
        return {"error": "missing"} if value is _MISSING else {"ok": copy.deepcopy(value)}
    if op == "delete":
        value = state.pop(command["key"], _MISSING)
        return {"error": "missing"} if value is _MISSING else {"ok": copy.deepcopy(value)}
    if op == "expect":
        value = state.get(command["key"], _MISSING)
        if value is _MISSING or value != command["value"]:
            return {"error": "expectation"}
        return {"ok": True}
    if op == "begin":
        stack.append(copy.deepcopy(state))
        return {"ok": len(stack)}
    if op == "commit":
        if not stack:
            return {"error": "transaction"}
        stack.pop()
        return {"ok": len(stack)}
    if op == "rollback":
        if not stack:
            return {"error": "transaction"}
        snapshot = stack.pop()
        state.clear()
        state.update(copy.deepcopy(snapshot))
        return {"ok": len(stack)}
    if op == "list":
        return {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}
    return {"error": "command"}


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    stack = []
    cache = {}
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue

        command_id = command.get("id", _MISSING)
        # Invalid supplied IDs are ordinary command errors, including explicit null.
        if command_id is not _MISSING and not isinstance(command_id, str):
            events.append({"error": "command"})
            continue

        identity = _identity(command)
        if command_id is not _MISSING and command_id in cache:
            previous_identity, previous_event = cache[command_id]
            if identity == previous_identity:
                events.append(copy.deepcopy(previous_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        op = _valid_command(command)
        if op is None:
            event = {"error": "command"}
        else:
            event = _execute(op, command, state, stack)

        events.append(copy.deepcopy(event))
        if command_id is not _MISSING and "ok" in event:
            cache[command_id] = (copy.deepcopy(identity), copy.deepcopy(event))

    return json.dumps(
        {
            "events": events,
            "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
            "depth": len(stack),
        },
        ensure_ascii=False,
    )
