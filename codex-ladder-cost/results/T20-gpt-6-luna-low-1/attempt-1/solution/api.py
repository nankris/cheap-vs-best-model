import copy
import json

from render import present
from service import compute


_MISSING = object()
_REQUIRED = {
    "put": ("key", "input"),
    "get": ("key",),
    "delete": ("key",),
    "begin": (),
    "commit": (),
    "rollback": (),
    "expect": ("key", "value"),
    "list": (),
}


def _command_error():
    return {"error": "command"}


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _valid(command):
    op = command.get("op", _MISSING)
    if not isinstance(op, str) or op not in _REQUIRED:
        return False
    for field in _REQUIRED[op]:
        if field not in command:
            return False
    if op in ("put", "get", "delete", "expect") and not isinstance(command["key"], str):
        return False
    return True


def _execute(command, state, stack):
    op = command["op"]
    if op == "put":
        key = command["key"]
        result = compute(copy.deepcopy(command["input"]))
        value = json.loads(present(result))
        state[key] = copy.deepcopy(value)
        return {"ok": copy.deepcopy(value)}
    if op == "get":
        if command["key"] not in state:
            return {"error": "missing"}
        return {"ok": copy.deepcopy(state[command["key"]])}
    if op == "delete":
        if command["key"] not in state:
            return {"error": "missing"}
        return {"ok": copy.deepcopy(state.pop(command["key"]))}
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
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    if op == "list":
        return {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}
    return _command_error()


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

    state = {}
    stack = []
    cache = {}
    events = []
    for command in commands:
        if not isinstance(command, dict):
            events.append(_command_error())
            continue

        if "id" in command and not isinstance(command["id"], str):
            events.append(_command_error())
            continue

        command_id = command.get("id", _MISSING)
        if command_id is not _MISSING and command_id in cache:
            identity = _identity(command)
            cached_identity, cached_event = cache[command_id]
            if identity == cached_identity:
                events.append(copy.deepcopy(cached_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        if not _valid(command):
            events.append(_command_error())
            continue

        event = _execute(command, state, stack)
        events.append(copy.deepcopy(event))
        if command_id is not _MISSING and "ok" in event:
            cache[command_id] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))

    output = {
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(output, ensure_ascii=False)
