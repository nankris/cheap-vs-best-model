"""JSON API for the transactional, idempotent state journal."""

import copy
import json

from service import compute


_MISSING = object()


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _valid_command(command):
    if not isinstance(command, dict):
        return False
    if "id" in command and not isinstance(command["id"], str):
        return False
    op = command.get("op", _MISSING)
    if not isinstance(op, str):
        return False
    required = {
        "put": ("key", "input"),
        "get": ("key",),
        "delete": ("key",),
        "expect": ("key", "value"),
        "begin": (),
        "commit": (),
        "rollback": (),
        "list": (),
    }
    if op not in required:
        return False
    for field in required[op]:
        if field not in command:
            return False
    if "key" in required[op] and not isinstance(command["key"], str):
        return False
    return True


def _process(commands):
    state = {}
    stack = []
    cache = {}
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue

        command_id = command.get("id", _MISSING)
        if command_id is not _MISSING and not isinstance(command_id, str):
            events.append({"error": "command"})
            continue

        if command_id is not _MISSING and command_id in cache:
            identity, event = cache[command_id]
            if _identity(command) == identity:
                events.append(copy.deepcopy(event))
            else:
                events.append({"error": "id-conflict"})
            continue

        if not _valid_command(command):
            events.append({"error": "command"})
            continue

        op = command["op"]
        key = command.get("key")
        if op == "put":
            # compute() returns an owned Result; take another copy before storing
            # it so neither the algorithm nor subsequent events can alias state.
            value = copy.deepcopy(compute(command["input"]).value)
            state[key] = value
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            if key not in state:
                event = {"error": "missing"}
            else:
                event = {"ok": copy.deepcopy(state[key])}
        elif op == "delete":
            if key not in state:
                event = {"error": "missing"}
            else:
                event = {"ok": copy.deepcopy(state.pop(key))}
        elif op == "begin":
            stack.append(copy.deepcopy(state))
            event = {"ok": len(stack)}
        elif op == "commit":
            if not stack:
                event = {"error": "transaction"}
            else:
                stack.pop()
                event = {"ok": len(stack)}
        elif op == "rollback":
            if not stack:
                event = {"error": "transaction"}
            else:
                state = stack.pop()
                event = {"ok": len(stack)}
        elif op == "expect":
            event = {"ok": True} if key in state and state[key] == command["value"] else {"error": "expectation"}
        else:  # list
            event = {"ok": [[item_key, copy.deepcopy(state[item_key])] for item_key in sorted(state)]}

        if "ok" in event and command_id is not _MISSING:
            cache[command_id] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))
        events.append(event)

    return {"events": events,
            "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
            "depth": len(stack)}


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")
    return json.dumps(_process(commands), ensure_ascii=False)
