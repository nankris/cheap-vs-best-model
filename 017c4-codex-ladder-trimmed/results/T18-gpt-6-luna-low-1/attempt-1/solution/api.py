"""JSON command journal API."""

import copy
import json

from model import Result
from render import present
from service import compute


_MISSING = object()


def _event_error(name):
    return {"error": name}


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _valid_command(command):
    """Validate command shape and fields before any command effects."""
    if not isinstance(command, dict):
        return False
    if "id" in command and not isinstance(command["id"], str):
        return False
    op = command.get("op", _MISSING)
    if not isinstance(op, str) or op not in {
        "put", "get", "delete", "begin", "commit", "rollback", "expect", "list"
    }:
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
    }[op]
    for field in required:
        if field not in command:
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
        # A string id is enough to perform a replay/conflict lookup, even if
        # the rest of the command is malformed.
        if isinstance(command, dict):
            supplied_id = command.get("id", _MISSING)
            if isinstance(supplied_id, str) and supplied_id in cache:
                original_identity, original_event = cache[supplied_id]
                if _identity(command) == original_identity:
                    events.append(copy.deepcopy(original_event))
                else:
                    events.append(_event_error("id-conflict"))
                continue

        if not _valid_command(command):
            events.append(_event_error("command"))
            continue

        op = command["op"]
        key = command.get("key")
        if op == "put":
            result = compute(copy.deepcopy(command["input"]))
            # Exercise the required presentation pipeline, then decode the
            # JSON scalar/list/null back into the journal's value domain.
            value = json.loads(present(result))
            state[key] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            if key not in state:
                event = _event_error("missing")
            else:
                event = {"ok": copy.deepcopy(state[key])}
        elif op == "delete":
            if key not in state:
                event = _event_error("missing")
            else:
                event = {"ok": copy.deepcopy(state.pop(key))}
        elif op == "begin":
            stack.append(copy.deepcopy(state))
            event = {"ok": len(stack)}
        elif op == "commit":
            if not stack:
                event = _event_error("transaction")
            else:
                stack.pop()
                event = {"ok": len(stack)}
        elif op == "rollback":
            if not stack:
                event = _event_error("transaction")
            else:
                state = stack.pop()
                event = {"ok": len(stack)}
        elif op == "expect":
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = _event_error("expectation")
        else:  # list
            event = {"ok": [[name, copy.deepcopy(state[name])] for name in sorted(state)]}

        events.append(copy.deepcopy(event))
        supplied_id = command.get("id", _MISSING)
        if isinstance(supplied_id, str) and "ok" in event:
            cache[supplied_id] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))

    output = {
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(output, ensure_ascii=True)
