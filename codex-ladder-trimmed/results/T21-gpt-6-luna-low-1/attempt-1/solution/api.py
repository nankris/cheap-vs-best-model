import copy
import json

from service import compute


def _missing():
    return {"error": "missing"}


def _command_error():
    return {"error": "command"}


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


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

        has_id = "id" in command
        command_id = command.get("id")
        if has_id and not isinstance(command_id, str):
            events.append(_command_error())
            continue

        if has_id and command_id in cache:
            identity, original_event = cache[command_id]
            if _identity(command) == identity:
                events.append(copy.deepcopy(original_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        op = command.get("op")
        if not isinstance(op, str) or op not in {
            "put", "get", "delete", "begin", "commit", "rollback", "expect", "list"
        }:
            event = _command_error()
        else:
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
                event = _command_error()
            elif any(not isinstance(command[field], str) for field in ("key",) if field in required):
                event = _command_error()
            elif op == "put":
                value = compute(command["input"]).value
                state[command["key"]] = copy.deepcopy(value)
                event = {"ok": copy.deepcopy(value)}
            elif op == "get":
                key = command["key"]
                event = {"ok": copy.deepcopy(state[key])} if key in state else _missing()
            elif op == "delete":
                key = command["key"]
                event = {"ok": copy.deepcopy(state.pop(key))} if key in state else _missing()
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
                event = {"ok": True} if command["key"] in state and state[command["key"]] == command["value"] else {"error": "expectation"}
            else:  # list
                event = {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}

        if has_id and "ok" in event:
            cache[command_id] = (copy.deepcopy(_identity(command)), copy.deepcopy(event))
        events.append(copy.deepcopy(event))

    response = {
        "events": events,
        "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    }
    return json.dumps(response, ensure_ascii=False)
