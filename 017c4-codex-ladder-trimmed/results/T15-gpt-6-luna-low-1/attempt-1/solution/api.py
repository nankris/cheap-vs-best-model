import copy
import json

from service import compute


_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _valid_command(command):
    if not isinstance(command, dict):
        return False
    op = command.get("op")
    if not isinstance(op, str) or op not in _OPS:
        return False
    if "id" in command and not isinstance(command["id"], str):
        return False
    if op in ("put", "get", "delete", "expect"):
        if "key" not in command or not isinstance(command["key"], str):
            return False
    if op == "put" and "input" not in command:
        return False
    if op == "expect" and "value" not in command:
        return False
    return True


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

    state = {}
    stack = []
    cache = {}
    events = []

    for command in commands:
        if isinstance(command, dict):
            supplied_id = command.get("id")
            id_is_valid = "id" not in command or isinstance(supplied_id, str)
            if id_is_valid and isinstance(supplied_id, str) and supplied_id in cache:
                identity = _identity(command)
                if identity == cache[supplied_id][0]:
                    event = copy.deepcopy(cache[supplied_id][1])
                else:
                    event = {"error": "id-conflict"}
                events.append(event)
                continue

        if not _valid_command(command):
            events.append({"error": "command"})
            continue

        op = command["op"]
        event = None
        if op == "put":
            value = copy.deepcopy(compute(command["input"]).value)
            state[command["key"]] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            key = command["key"]
            if key in state:
                event = {"ok": copy.deepcopy(state[key])}
            else:
                event = {"error": "missing"}
        elif op == "delete":
            key = command["key"]
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
            key = command["key"]
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = {"error": "expectation"}
        elif op == "list":
            event = {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}

        events.append(event)
        if "ok" in event and "id" in command:
            cache[command["id"]] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))

    result = {
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(result, ensure_ascii=False)
