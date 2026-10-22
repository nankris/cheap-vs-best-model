"""JSON command journal with nested savepoints and idempotent replay."""

from copy import deepcopy
import json

from service import compute
from render import present


_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}
_KEY_OPS = {"put", "get", "delete", "expect"}


def _valid_command(command):
    op = command.get("op")
    if not isinstance(op, str) or op not in _OPS:
        return False
    if op in _KEY_OPS and not isinstance(command.get("key"), str):
        return False
    if op == "put" and "input" not in command:
        return False
    if op == "expect" and "value" not in command:
        return False
    return True


def _listing(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def _execute(command, state, stack):
    op = command["op"]
    if op == "put":
        value = json.loads(present(compute(deepcopy(command["input"]))))
        state[command["key"]] = deepcopy(value)
        return {"ok": deepcopy(value)}
    if op in {"get", "delete"}:
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        value = deepcopy(state[key])
        if op == "delete":
            del state[key]
        return {"ok": value}
    if op == "begin":
        stack.append(deepcopy(state))
        return {"ok": len(stack)}
    if op in {"commit", "rollback"}:
        if not stack:
            return {"error": "transaction"}
        snapshot = stack.pop()
        if op == "rollback":
            state.clear()
            state.update(deepcopy(snapshot))
        return {"ok": len(stack)}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    return {"ok": _listing(state)}


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
        command_id = command.get("id")
        if has_id and not isinstance(command_id, str):
            events.append({"error": "command"})
            continue

        identity = {key: value for key, value in command.items() if key != "id"}
        if has_id and command_id in cache:
            original_identity, original_event = cache[command_id]
            events.append(
                deepcopy(original_event)
                if identity == original_identity
                else {"error": "id-conflict"}
            )
            continue

        if not _valid_command(command):
            events.append({"error": "command"})
            continue

        event = _execute(command, state, stack)
        if has_id and "ok" in event:
            cache[command_id] = deepcopy(identity), deepcopy(event)
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _listing(state), "depth": len(stack)})
