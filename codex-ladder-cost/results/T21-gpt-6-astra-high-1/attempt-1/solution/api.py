"""JSON command journal with savepoints and successful-event replay."""

from copy import deepcopy
import json

import render
import service


_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}
_KEY_OPS = {"put", "get", "delete", "expect"}


def _listing(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def _execute(command, state, stack):
    """Validate completely before changing state or savepoints."""
    op = command.get("op")
    if not isinstance(op, str) or op not in _OPS:
        return {"error": "command"}
    if op in _KEY_OPS and not isinstance(command.get("key"), str):
        return {"error": "command"}
    if op == "put" and "input" not in command:
        return {"error": "command"}
    if op == "expect" and "value" not in command:
        return {"error": "command"}

    if op == "put":
        result = service.compute(deepcopy(command["input"]))
        value = json.loads(render.present(result))
        state[command["key"]] = deepcopy(value)
        return {"ok": deepcopy(value)}
    if op in {"get", "delete"}:
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
            identity = {key: value for key, value in command.items() if key != "id"}
            command_id = command["id"]
            if command_id in cache:
                previous_identity, previous_event = cache[command_id]
                if identity == previous_identity:
                    events.append(deepcopy(previous_event))
                else:
                    events.append({"error": "id-conflict"})
                continue

        event = _execute(command, state, stack)
        if has_id and "ok" in event:
            cache[command_id] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _listing(state), "depth": len(stack)})
