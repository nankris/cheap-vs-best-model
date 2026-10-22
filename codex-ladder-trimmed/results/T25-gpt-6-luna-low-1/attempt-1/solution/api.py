import copy
import json

from service import compute


def _event_error(name):
    return {"error": name}


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
            events.append(_event_error("command"))
            continue

        has_id = "id" in command
        command_id = command.get("id")
        if has_id and not isinstance(command_id, str):
            events.append(_event_error("command"))
            continue

        identity = _identity(command) if has_id else None
        if has_id and command_id in cache:
            old_identity, old_event = cache[command_id]
            if old_identity == identity:
                events.append(copy.deepcopy(old_event))
            else:
                events.append(_event_error("id-conflict"))
            continue

        op = command.get("op")
        if not isinstance(op, str) or op not in {
            "put", "get", "delete", "begin", "commit", "rollback", "expect", "list"
        }:
            events.append(_event_error("command"))
            continue

        required = {
            "put": ("key", "input"),
            "get": ("key",),
            "delete": ("key",),
            "expect": ("key", "value"),
            "begin": (), "commit": (), "rollback": (), "list": (),
        }[op]
        if any(field not in command for field in required):
            events.append(_event_error("command"))
            continue
        if "key" in required and not isinstance(command["key"], str):
            events.append(_event_error("command"))
            continue

        key = command.get("key")
        if op == "put":
            try:
                computed = compute(copy.deepcopy(command["input"])).value
            except Exception:
                # Algorithm inputs are specified as valid; preserve atomicity if
                # an unexpected malformed value reaches the implementation.
                events.append(_event_error("command"))
                continue
            value = copy.deepcopy(computed)
            state[key] = value
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
                old = state.pop(key)
                event = {"ok": copy.deepcopy(old)}
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

        if has_id and "ok" in event:
            cache[command_id] = (copy.deepcopy(identity), copy.deepcopy(event))
        events.append(copy.deepcopy(event))

    output_state = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return json.dumps({"events": events, "state": output_state, "depth": len(stack)}, ensure_ascii=True)
