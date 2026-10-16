import copy
import json

from service import compute


_MISSING = object()
_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}


def _command_error():
    return {"error": "command"}


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

        supplied_id = command.get("id", _MISSING)
        if supplied_id is not _MISSING and not isinstance(supplied_id, str):
            events.append(_command_error())
            continue

        identity = {key: value for key, value in command.items() if key != "id"}
        if supplied_id is not _MISSING and supplied_id in cache:
            prior_identity, prior_event = cache[supplied_id]
            if prior_identity == identity:
                events.append(copy.deepcopy(prior_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        op = command.get("op", _MISSING)
        if not isinstance(op, str) or op not in _OPS:
            events.append(_command_error())
            continue

        needs_key = op in {"put", "get", "delete", "expect"}
        if needs_key and ("key" not in command or not isinstance(command["key"], str)):
            events.append(_command_error())
            continue
        if op == "put" and "input" not in command:
            events.append(_command_error())
            continue
        if op == "expect" and "value" not in command:
            events.append(_command_error())
            continue

        key = command.get("key")
        event = None
        if op == "put":
            value = compute(command["input"]).value
            state[key] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            if key in state:
                event = {"ok": copy.deepcopy(state[key])}
            else:
                event = {"error": "missing"}
        elif op == "delete":
            if key in state:
                event = {"ok": copy.deepcopy(state.pop(key))}
            else:
                event = {"error": "missing"}
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
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = {"error": "expectation"}
        elif op == "list":
            event = {"ok": [[name, copy.deepcopy(state[name])] for name in sorted(state)]}

        events.append(event)
        if supplied_id is not _MISSING and "ok" in event:
            cache[supplied_id] = (copy.deepcopy(identity), copy.deepcopy(event))

    result = {
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(result, ensure_ascii=True)
