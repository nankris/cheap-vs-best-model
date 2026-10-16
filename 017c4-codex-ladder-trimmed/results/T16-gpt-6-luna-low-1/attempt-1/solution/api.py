import copy
import json

from render import present
from service import compute


_MISSING = object()


def _error(name):
    return {"error": name}


def _valid_command(command):
    """Validate command shape and required fields before execution."""
    if not isinstance(command, dict):
        return None

    op = command.get("op", _MISSING)
    if op not in ("put", "get", "delete", "begin", "commit", "rollback", "expect", "list"):
        return None

    required = {
        "put": ("key", "input"),
        "get": ("key",),
        "delete": ("key",),
        "expect": ("key", "value"),
        "begin": (),
        "commit": (),
        "rollback": (),
        "list": (),
    }[op]
    if any(field not in command for field in required):
        return None
    if "key" in required and not isinstance(command["key"], str):
        return None
    return op


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    stack = []
    # id -> (identity, original successful event), both owned by the cache
    cache = {}
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append(_error("command"))
            continue

        supplied_id = command.get("id", _MISSING)
        if supplied_id is not _MISSING and not isinstance(supplied_id, str):
            events.append(_error("command"))
            continue

        identity = {key: value for key, value in command.items() if key != "id"}
        if isinstance(supplied_id, str) and supplied_id in cache:
            cached_identity, cached_event = cache[supplied_id]
            if identity == cached_identity:
                events.append(copy.deepcopy(cached_event))
            else:
                events.append(_error("id-conflict"))
            continue

        op = _valid_command(command)
        if op is None:
            events.append(_error("command"))
            continue

        # Create a detached event value before storing it or returning it.
        if op == "put":
            result = compute(command["input"])
            rendered = present(result)
            value = json.loads(rendered)
            state[command["key"]] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            key = command["key"]
            if key not in state:
                event = _error("missing")
            else:
                event = {"ok": copy.deepcopy(state[key])}
        elif op == "delete":
            key = command["key"]
            if key not in state:
                event = _error("missing")
            else:
                event = {"ok": copy.deepcopy(state.pop(key))}
        elif op == "begin":
            stack.append(copy.deepcopy(state))
            event = {"ok": len(stack)}
        elif op == "commit":
            if not stack:
                event = _error("transaction")
            else:
                stack.pop()
                event = {"ok": len(stack)}
        elif op == "rollback":
            if not stack:
                event = _error("transaction")
            else:
                state = copy.deepcopy(stack.pop())
                event = {"ok": len(stack)}
        elif op == "expect":
            key = command["key"]
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = _error("expectation")
        else:  # list
            event = {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}

        # State and stack hold their own copies; each event is independently owned.
        events.append(copy.deepcopy(event))
        if isinstance(supplied_id, str) and "ok" in event:
            cache[supplied_id] = (copy.deepcopy(identity), copy.deepcopy(event))

    return json.dumps(
        {"events": events, "state": [[key, state[key]] for key in sorted(state)], "depth": len(stack)},
        ensure_ascii=False,
    )
