"""JSON API for the transactional journal."""

from copy import deepcopy
import json

from render import present
from service import compute


_MISSING = object()


def _event_error(name):
    return {"error": name}


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    stack = []
    id_cache = {}
    events = []

    for command in commands:
        # Invalid command objects and invalid ids are rejected before any
        # cache lookup. A valid id lookup precedes all other validation.
        if not isinstance(command, dict):
            events.append(_event_error("command"))
            continue

        supplied_id = command.get("id", _MISSING)
        if supplied_id is not _MISSING and not isinstance(supplied_id, str):
            events.append(_event_error("command"))
            continue

        identity = {key: deepcopy(value) for key, value in command.items() if key != "id"}
        if supplied_id is not _MISSING and supplied_id in id_cache:
            cached_identity, cached_event = id_cache[supplied_id]
            if identity == cached_identity:
                events.append(deepcopy(cached_event))
            else:
                events.append(_event_error("id-conflict"))
            continue

        op = command.get("op", _MISSING)
        key = command.get("key", _MISSING)
        result = None

        # Validate the complete command shape before performing any action.
        if not isinstance(op, str):
            event = _event_error("command")
        elif op == "put":
            if key is _MISSING or not isinstance(key, str) or "input" not in command:
                event = _event_error("command")
            else:
                # compute/present are the public algorithm pipeline. The
                # serialized result is parsed back to preserve JSON scalar,
                # list, and null values as journal values.
                rendered = present(compute(command["input"]))
                value = json.loads(rendered)
                state[key] = deepcopy(value)
                event = {"ok": deepcopy(value)}
        elif op in ("get", "delete"):
            if key is _MISSING or not isinstance(key, str):
                event = _event_error("command")
            elif key not in state:
                event = _event_error("missing")
            elif op == "get":
                event = {"ok": deepcopy(state[key])}
            else:
                event = {"ok": deepcopy(state.pop(key))}
        elif op == "expect":
            if key is _MISSING or not isinstance(key, str) or "value" not in command:
                event = _event_error("command")
            elif key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = _event_error("expectation")
        elif op == "begin":
            stack.append(deepcopy(state))
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
        elif op == "list":
            event = {"ok": [[item_key, deepcopy(state[item_key])] for item_key in sorted(state)]}
        else:
            event = _event_error("command")

        if supplied_id is not _MISSING and "ok" in event:
            id_cache[supplied_id] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps(
        {
            "events": events,
            "state": [[key, deepcopy(state[key])] for key in sorted(state)],
            "depth": len(stack),
        },
        ensure_ascii=False,
    )
