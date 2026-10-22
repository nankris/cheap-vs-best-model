import copy
import json

from service import compute
from render import present


_MISSING = object()
_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _valid_command(command):
    if not isinstance(command, dict):
        return False
    if "id" in command and not isinstance(command["id"], str):
        return False
    op = command.get("op", _MISSING)
    if op not in _OPS:
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


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    stack = []
    cache = {}
    events = []

    for command in commands:
        # Valid id lookup happens before ordinary command validation.
        if isinstance(command, dict) and isinstance(command.get("id"), str):
            command_id = command["id"]
            identity = _identity(command)
            if command_id in cache:
                cached_identity, cached_event = cache[command_id]
                if identity == cached_identity:
                    events.append(copy.deepcopy(cached_event))
                else:
                    events.append({"error": "id-conflict"})
                continue

        if not _valid_command(command):
            events.append({"error": "command"})
            continue

        op = command["op"]
        key = command.get("key")
        if op == "put":
            # Rendering is the canonical JSON boundary for algorithm results.
            value = json.loads(present(compute(command["input"])))
            state[key] = copy.deepcopy(value)
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
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = {"error": "expectation"}
        elif op == "list":
            event = {"ok": [[item_key, copy.deepcopy(state[item_key])] for item_key in sorted(state)]}

        events.append(event)
        if "ok" in event and "id" in command:
            cache[command["id"]] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))

    return json.dumps({
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }, ensure_ascii=False)
