"""A per-invocation journal with savepoints and idempotent commands."""

from copy import deepcopy
import json

from service import compute
from render import present


def _valid_command(command):
    op = command.get("op")
    if not isinstance(op, str) or op not in (
        "put", "get", "delete", "begin", "commit", "rollback", "expect", "list"
    ):
        return False
    if op in ("put", "get", "delete", "expect"):
        if "key" not in command or not isinstance(command["key"], str):
            return False
    if op == "put" and "input" not in command:
        return False
    if op == "expect" and "value" not in command:
        return False
    return True


def _entries(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def _execute(command, state, stack):
    op = command["op"]
    if op == "put":
        value = json.loads(present(compute(deepcopy(command["input"]))))
        state[command["key"]] = deepcopy(value)
        return {"ok": deepcopy(value)}
    if op in ("get", "delete"):
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        value = deepcopy(state[key])
        if op == "delete":
            del state[key]
        return {"ok": value}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    if op == "list":
        return {"ok": _entries(state)}
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


def run(payload):
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
            previous_identity, previous_event = cache[command_id]
            if identity == previous_identity:
                events.append(deepcopy(previous_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        if not _valid_command(command):
            events.append({"error": "command"})
            continue

        event = _execute(command, state, stack)
        if has_id and "ok" in event:
            cache[command_id] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _entries(state), "depth": len(stack)})
