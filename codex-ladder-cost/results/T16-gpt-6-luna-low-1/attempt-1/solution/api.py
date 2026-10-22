import copy
import json

from render import present
from service import compute


_INVALID = object()


def _is_command_error(command):
    if not isinstance(command, dict):
        return True

    if "id" in command and not isinstance(command["id"], str):
        return True

    op = command.get("op", _INVALID)
    if op not in {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}:
        return True

    if op in {"put", "get", "delete", "expect"}:
        if "key" not in command or not isinstance(command["key"], str):
            return True
    if op == "put" and "input" not in command:
        return True
    if op == "expect" and "value" not in command:
        return True
    return False


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _execute(command, state, stack):
    op = command["op"]

    if op == "put":
        key = command["key"]
        algorithm_value = json.loads(present(compute(copy.deepcopy(command["input"]))))
        state[key] = copy.deepcopy(algorithm_value)
        return {"ok": copy.deepcopy(algorithm_value)}

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
            return {"error": "transaction"}
        stack.pop()
        return {"ok": len(stack)}

    if op == "rollback":
        if not stack:
            return {"error": "transaction"}
        restored = stack.pop()
        state.clear()
        state.update(copy.deepcopy(restored))
        return {"ok": len(stack)}

    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}

    if op == "list":
        return {"ok": copy.deepcopy([[key, state[key]] for key in sorted(state)])}

    return {"error": "command"}


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    stack = []
    cache = []
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue

        if "id" in command and not isinstance(command["id"], str):
            events.append({"error": "command"})
            continue

        command_id = command.get("id", _INVALID)
        command_identity = _identity(command)
        cached = None
        if command_id is not _INVALID:
            for existing_id, existing_identity, event in cache:
                if existing_id == command_id:
                    cached = (existing_identity, event)
                    break
            if cached is not None:
                if cached[0] == command_identity:
                    events.append(copy.deepcopy(cached[1]))
                else:
                    events.append({"error": "id-conflict"})
                continue

        if _is_command_error(command):
            event = {"error": "command"}
        else:
            event = _execute(command, state, stack)

        event_copy = copy.deepcopy(event)
        events.append(event_copy)
        if command_id is not _INVALID and "ok" in event:
            cache.append((command_id, copy.deepcopy(command_identity), copy.deepcopy(event)))

    output_state = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return json.dumps({"events": events, "state": output_state, "depth": len(stack)}, ensure_ascii=False)
