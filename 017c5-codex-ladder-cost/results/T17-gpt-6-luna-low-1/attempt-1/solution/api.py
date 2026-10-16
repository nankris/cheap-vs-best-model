import copy
import json

from service import compute


def _command_error():
    return {"error": "command"}


def _valid_command(command):
    if not isinstance(command, dict):
        return False
    if "id" in command and not isinstance(command["id"], str):
        return False
    op = command.get("op")
    if not isinstance(op, str) or op not in {
        "put", "get", "delete", "begin", "commit", "rollback", "expect", "list"
    }:
        return False
    required = {
        "put": ("key", "input"),
        "get": ("key",),
        "delete": ("key",),
        "expect": ("key", "value"),
    }.get(op, ())
    if any(field not in command for field in required):
        return False
    if "key" in required and not isinstance(command["key"], str):
        return False
    return True


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


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

        # Invalid supplied ids are command errors, even if a similar command is cached.
        if "id" in command and not isinstance(command["id"], str):
            events.append(_command_error())
            continue

        command_id = command.get("id")
        if isinstance(command_id, str) and command_id in cache:
            identity, event = cache[command_id]
            if identity == _identity(command):
                events.append(copy.deepcopy(event))
            else:
                events.append({"error": "id-conflict"})
            continue

        if not _valid_command(command):
            events.append(_command_error())
            continue

        op = command["op"]
        event = None
        if op == "put":
            value = compute(command["input"]).value
            state[command["key"]] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            key = command["key"]
            event = {"ok": copy.deepcopy(state[key])} if key in state else {"error": "missing"}
        elif op == "delete":
            key = command["key"]
            event = {"ok": copy.deepcopy(state.pop(key))} if key in state else {"error": "missing"}
        elif op == "begin":
            stack.append(copy.deepcopy(state))
            event = {"ok": len(stack)}
        elif op == "commit":
            if stack:
                stack.pop()
                event = {"ok": len(stack)}
            else:
                event = {"error": "transaction"}
        elif op == "rollback":
            if stack:
                state = stack.pop()
                event = {"ok": len(stack)}
            else:
                event = {"error": "transaction"}
        elif op == "expect":
            key = command["key"]
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = {"error": "expectation"}
        elif op == "list":
            event = {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}

        events.append(event)
        if "ok" in event and isinstance(command_id, str):
            cache[command_id] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))

    output_state = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return json.dumps({"events": events, "state": output_state, "depth": len(stack)}, ensure_ascii=True)
