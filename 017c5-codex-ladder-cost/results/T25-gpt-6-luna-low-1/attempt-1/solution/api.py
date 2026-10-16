import copy
import json

from service import compute


_MISSING = object()


def _event_error(name):
    return {"error": name}


def _identity(command):
    return {key: copy.deepcopy(value) for key, value in command.items() if key != "id"}


def _valid(command):
    op = command.get("op", _MISSING)
    if not isinstance(op, str):
        return False
    if op in ("begin", "commit", "rollback", "list"):
        return True
    if op in ("put", "get", "delete"):
        return isinstance(command.get("key", _MISSING), str) and (op != "put" or "input" in command)
    if op == "expect":
        return isinstance(command.get("key", _MISSING), str) and "value" in command
    return False


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
            prior_identity, prior_event = cache[command_id]
            if identity == prior_identity:
                events.append(copy.deepcopy(prior_event))
            else:
                events.append(_event_error("id-conflict"))
            continue
        if not _valid(command):
            events.append(_event_error("command"))
            continue

        op = command["op"]
        if op == "put":
            key = command["key"]
            result = compute(copy.deepcopy(command["input"]))
            value = copy.deepcopy(result.value)
            state[key] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            key = command["key"]
            event = {"ok": copy.deepcopy(state[key])} if key in state else _event_error("missing")
        elif op == "delete":
            key = command["key"]
            if key in state:
                event = {"ok": copy.deepcopy(state.pop(key))}
            else:
                event = _event_error("missing")
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
                state = copy.deepcopy(stack.pop())
                event = {"ok": len(stack)}
        elif op == "expect":
            key = command["key"]
            event = {"ok": True} if key in state and state[key] == command["value"] else _event_error("expectation")
        else:  # list
            event = {"ok": [[key, copy.deepcopy(state[key])] for key in sorted(state)]}

        if has_id and "ok" in event:
            cache[command_id] = (copy.deepcopy(identity), copy.deepcopy(event))
        events.append(copy.deepcopy(event))

    ordered_state = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return json.dumps({"events": events, "state": ordered_state, "depth": len(stack)}, ensure_ascii=False)
