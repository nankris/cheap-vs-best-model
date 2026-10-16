import copy
import json

from service import compute


_MISSING = object()


def _event_error(name):
    return {"error": name}


def _valid_command(command):
    """Validate ordinary command shape; return its op or None."""
    if not isinstance(command, dict):
        return None
    op = command.get("op", _MISSING)
    if op not in ("put", "get", "delete", "begin", "commit", "rollback", "expect", "list"):
        return None
    if "id" in command and not isinstance(command["id"], str):
        return None
    if op in ("put", "get", "delete", "expect"):
        if "key" not in command or not isinstance(command["key"], str):
            return None
    if op == "put" and "input" not in command:
        return None
    if op == "expect" and "value" not in command:
        return None
    return op


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

    state = {}
    stack = []
    cache = []  # Ordered pairs preserve Python equality semantics for JSON structures.
    events = []

    for command in commands:
        # Invalid ids are rejected before cache lookup; non-dicts are command errors.
        if not isinstance(command, dict):
            events.append(_event_error("command"))
            continue
        supplied_id = command.get("id", _MISSING)
        if supplied_id is not _MISSING and not isinstance(supplied_id, str):
            events.append(_event_error("command"))
            continue

        if supplied_id is not _MISSING:
            identity = {key: value for key, value in command.items() if key != "id"}
            found = False
            for cached_id, cached_identity, cached_event in cache:
                if supplied_id == cached_id:
                    found = True
                    if identity == cached_identity:
                        events.append(copy.deepcopy(cached_event))
                    else:
                        events.append(_event_error("id-conflict"))
                    break
            if found:
                continue

        op = _valid_command(command)
        if op is None:
            events.append(_event_error("command"))
            continue

        key = command.get("key")
        if op == "put":
            value = copy.deepcopy(compute(copy.deepcopy(command["input"])).value)
            state[key] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            event = {"ok": copy.deepcopy(state[key])} if key in state else _event_error("missing")
        elif op == "delete":
            if key in state:
                event = {"ok": copy.deepcopy(state.pop(key))}
            else:
                event = _event_error("missing")
        elif op == "begin":
            stack.append(copy.deepcopy(state))
            event = {"ok": len(stack)}
        elif op == "commit":
            if stack:
                stack.pop()
                event = {"ok": len(stack)}
            else:
                event = _event_error("transaction")
        elif op == "rollback":
            if stack:
                state = stack.pop()
                event = {"ok": len(stack)}
            else:
                event = _event_error("transaction")
        elif op == "expect":
            event = {"ok": True} if key in state and state[key] == command["value"] else _event_error("expectation")
        else:  # list
            event = {"ok": [[item_key, copy.deepcopy(state[item_key])] for item_key in sorted(state)]}

        # Every public event is detached from state, and successful ids retain
        # detached copies of both identity and event outside savepoints.
        event = copy.deepcopy(event)
        events.append(event)
        if supplied_id is not _MISSING and "ok" in event:
            cache.append((supplied_id, copy.deepcopy(identity), copy.deepcopy(event)))

    result = {
        "events": copy.deepcopy(events),
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(result, ensure_ascii=False)
