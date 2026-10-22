"""A per-invocation journal with savepoints and successful-event replay."""

from copy import deepcopy
import json

from service import compute
from render import present


_REQUIRED = {
    "put": ("key", "input"),
    "get": ("key",),
    "delete": ("key",),
    "expect": ("key", "value"),
    "begin": (),
    "commit": (),
    "rollback": (),
    "list": (),
}


def _listing(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def _execute(command, state, stack):
    op = command.get("op")
    if not isinstance(op, str) or op not in _REQUIRED:
        return {"error": "command"}
    required = _REQUIRED[op]
    if any(field not in command for field in required):
        return {"error": "command"}
    if "key" in required and not isinstance(command["key"], str):
        return {"error": "command"}

    if op == "put":
        value = json.loads(present(compute(deepcopy(command["input"]))))
        state[command["key"]] = deepcopy(value)
        return {"ok": deepcopy(value)}
    if op in ("get", "delete"):
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        value = state.pop(key) if op == "delete" else state[key]
        return {"ok": deepcopy(value)}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    if op == "list":
        return {"ok": _listing(state)}
    if op == "begin":
        stack.append(deepcopy(state))
        return {"ok": len(stack)}
    if not stack:
        return {"error": "transaction"}
    snapshot = stack.pop()
    if op == "rollback":
        state.clear()
        state.update(deepcopy(snapshot))
    return {"ok": len(stack)}


def run(payload: str) -> str:
    commands = json.loads(payload)
    state = {}
    stack = []
    cache = {}
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue
        has_id = "id" in command
        if has_id and not isinstance(command["id"], str):
            events.append({"error": "command"})
            continue

        if has_id:
            identifier = command["id"]
            identity = {key: value for key, value in command.items() if key != "id"}
            if identifier in cache:
                old_identity, old_event = cache[identifier]
                if identity == old_identity:
                    events.append(deepcopy(old_event))
                else:
                    events.append({"error": "id-conflict"})
                continue

        event = _execute(command, state, stack)
        if has_id and "ok" in event:
            cache[identifier] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _listing(state), "depth": len(stack)})
