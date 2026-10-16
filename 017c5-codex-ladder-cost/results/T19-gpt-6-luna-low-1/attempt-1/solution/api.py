import copy
import json

from service import compute
from render import present


_COMMAND_ERROR = {"error": "command"}
_TRANSACTION_ERROR = {"error": "transaction"}


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _valid(command):
    """Return an error event or None. This must run before command effects."""
    op = command.get("op")
    if not isinstance(op, str):
        return _COMMAND_ERROR
    if op not in {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}:
        return _COMMAND_ERROR
    if "id" in command and not isinstance(command["id"], str):
        return _COMMAND_ERROR
    if op in {"put", "get", "delete", "expect"}:
        if "key" not in command or not isinstance(command["key"], str):
            return _COMMAND_ERROR
    if op == "put" and "input" not in command:
        return _COMMAND_ERROR
    if op == "expect" and "value" not in command:
        return _COMMAND_ERROR
    return None


def _event(command, state, stack):
    op = command["op"]
    if op == "put":
        key = command["key"]
        result = compute(command["input"])
        rendered = present(result)
        value = json.loads(rendered)
        state[key] = copy.deepcopy(value)
        return {"ok": copy.deepcopy(value)}
    if op == "get":
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        return {"ok": copy.deepcopy(state[key])}
    if op == "delete":
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        return {"ok": copy.deepcopy(state.pop(key))}
    if op == "begin":
        stack.append(copy.deepcopy(state))
        return {"ok": len(stack)}
    if op == "commit":
        if not stack:
            return copy.deepcopy(_TRANSACTION_ERROR)
        stack.pop()
        return {"ok": len(stack)}
    if op == "rollback":
        if not stack:
            return copy.deepcopy(_TRANSACTION_ERROR)
        snapshot = stack.pop()
        state.clear()
        state.update(copy.deepcopy(snapshot))
        return {"ok": len(stack)}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    if op == "list":
        return {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}
    return copy.deepcopy(_COMMAND_ERROR)


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

    state = {}
    stack = []
    cache = []
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append(copy.deepcopy(_COMMAND_ERROR))
            continue

        supplied_id = command.get("id")
        has_valid_id = isinstance(supplied_id, str)
        if "id" in command and not has_valid_id:
            events.append(copy.deepcopy(_COMMAND_ERROR))
            continue

        if has_valid_id:
            identity = _identity(command)
            cached = next((entry for entry in cache if entry[0] == supplied_id), None)
            if cached is not None:
                if cached[1] == identity:
                    events.append(copy.deepcopy(cached[2]))
                else:
                    events.append({"error": "id-conflict"})
                continue

        validation_error = _valid(command)
        if validation_error is not None:
            events.append(copy.deepcopy(validation_error))
            continue

        event = _event(command, state, stack)
        events.append(copy.deepcopy(event))
        if has_valid_id and "ok" in event:
            cache.append((supplied_id, copy.deepcopy(_identity(command)), copy.deepcopy(event)))

    state_rows = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return json.dumps({"events": events, "state": state_rows, "depth": len(stack)}, ensure_ascii=False)
