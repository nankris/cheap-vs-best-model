import copy
import json

from render import present
from service import compute


_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}


def _valid_command(command):
    if not isinstance(command, dict):
        return False
    if "id" in command and not isinstance(command["id"], str):
        return False
    op = command.get("op")
    if not isinstance(op, str) or op not in _OPS:
        return False
    if op in {"put", "get", "delete", "expect"}:
        if "key" not in command or not isinstance(command["key"], str):
            return False
    if op == "put" and "input" not in command:
        return False
    if op == "expect" and "value" not in command:
        return False
    return True


def _error(name):
    return {"error": name}


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
            events.append(_error("command"))
            continue

        supplied_id = command.get("id")
        if "id" in command and not isinstance(supplied_id, str):
            events.append(_error("command"))
            continue

        identity = None
        if isinstance(supplied_id, str):
            identity = {key: value for key, value in command.items() if key != "id"}
            if supplied_id in cache:
                cached_identity, cached_event = cache[supplied_id]
                if cached_identity == identity:
                    events.append(copy.deepcopy(cached_event))
                else:
                    events.append(_error("id-conflict"))
                continue

        if not _valid_command(command):
            event = _error("command")
        else:
            op = command["op"]
            if op == "put":
                value = json.loads(present(compute(copy.deepcopy(command["input"]))))
                state[command["key"]] = copy.deepcopy(value)
                event = {"ok": copy.deepcopy(value)}
            elif op == "get":
                key = command["key"]
                event = {"ok": copy.deepcopy(state[key])} if key in state else _error("missing")
            elif op == "delete":
                key = command["key"]
                event = {"ok": copy.deepcopy(state.pop(key))} if key in state else _error("missing")
            elif op == "begin":
                stack.append(copy.deepcopy(state))
                event = {"ok": len(stack)}
            elif op == "commit":
                if stack:
                    stack.pop()
                    event = {"ok": len(stack)}
                else:
                    event = _error("transaction")
            elif op == "rollback":
                if stack:
                    state = stack.pop()
                    event = {"ok": len(stack)}
                else:
                    event = _error("transaction")
            elif op == "expect":
                key = command["key"]
                if key in state and state[key] == command["value"]:
                    event = {"ok": True}
                else:
                    event = _error("expectation")
            else:  # list
                event = {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}

        if identity is not None and "ok" in event:
            cache[supplied_id] = (copy.deepcopy(identity), copy.deepcopy(event))
        events.append(copy.deepcopy(event))

    output = {
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(output, ensure_ascii=False)
