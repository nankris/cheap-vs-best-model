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


def _entries(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def _execute(command, state, savepoints):
    """Execute a validated command, transferring values through deep copies."""
    op = command["op"]
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
        return {"ok": _entries(state)}
    if op == "begin":
        savepoints.append(deepcopy(state))
    else:
        if not savepoints:
            return {"error": "transaction"}
        snapshot = savepoints.pop()
        if op == "rollback":
            state.clear()
            state.update(deepcopy(snapshot))
    return {"ok": len(savepoints)}


def run(payload: str) -> str:
    commands = json.loads(payload)
    state = {}
    savepoints = []
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

        identity = {key: value for key, value in command.items() if key != "id"}
        if has_id and command["id"] in cache:
            old_identity, old_event = cache[command["id"]]
            if identity == old_identity:
                events.append(deepcopy(old_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        op = command.get("op")
        if (
            not isinstance(op, str)
            or op not in _REQUIRED
            or any(field not in command for field in _REQUIRED[op])
            or ("key" in _REQUIRED[op] and not isinstance(command["key"], str))
        ):
            events.append({"error": "command"})
            continue

        event = _execute(command, state, savepoints)
        if has_id and "ok" in event:
            cache[command["id"]] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _entries(state), "depth": len(savepoints)})
