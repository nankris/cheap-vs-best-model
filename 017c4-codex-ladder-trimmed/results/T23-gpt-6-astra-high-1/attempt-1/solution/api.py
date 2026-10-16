"""JSON journal with nested savepoints and invocation-local idempotency."""

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


def _ordered(state):
    return [[key, state[key]] for key in sorted(state)]


def _execute(command, state, stack):
    """Execute a validated command; the caller copies its returned event."""
    op = command["op"]
    if op == "put":
        value = json.loads(present(compute(deepcopy(command["input"]))))
        state[command["key"]] = deepcopy(value)
        return {"ok": value}
    if op in ("get", "delete"):
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        return {"ok": state.pop(key) if op == "delete" else state[key]}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    if op == "list":
        return {"ok": _ordered(state)}
    if op == "begin":
        stack.append(deepcopy(state))
    else:
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
        identifier = command.get("id")
        if has_id and not isinstance(identifier, str):
            events.append({"error": "command"})
            continue
        identity = {key: value for key, value in command.items() if key != "id"}
        # Replay/conflict resolution deliberately precedes command validation.
        if has_id and identifier in cache:
            previous_identity, previous_event = cache[identifier]
            if identity == previous_identity:
                events.append(deepcopy(previous_event))
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

        event = deepcopy(_execute(command, state, stack))
        if has_id and "ok" in event:
            cache[identifier] = (deepcopy(identity), deepcopy(event))
        events.append(event)

    return json.dumps({"events": events, "state": deepcopy(_ordered(state)), "depth": len(stack)})
