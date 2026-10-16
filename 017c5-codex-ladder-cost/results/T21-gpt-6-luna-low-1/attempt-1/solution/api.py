import copy
import json

from render import present
from service import compute


_MISSING = object()


def _event_json(value):
    return json.dumps(value, ensure_ascii=False)


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    stack = []
    cache = {}
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue

        supplied_id = command.get("id", _MISSING)
        if supplied_id is not _MISSING and not isinstance(supplied_id, str):
            events.append({"error": "command"})
            continue

        identity = {key: value for key, value in command.items() if key != "id"}
        if supplied_id is not _MISSING and supplied_id in cache:
            cached_identity, cached_event = cache[supplied_id]
            if identity == cached_identity:
                events.append(copy.deepcopy(cached_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        op = command.get("op", _MISSING)
        required = {
            "put": ("key", "input"),
            "get": ("key",),
            "delete": ("key",),
            "expect": ("key", "value"),
            "begin": (),
            "commit": (),
            "rollback": (),
            "list": (),
        }
        if op not in required:
            event = {"error": "command"}
        elif any(field not in command for field in required[op]):
            event = {"error": "command"}
        elif any(not isinstance(command[field], str) for field in ("key",) if field in required[op]):
            event = {"error": "command"}
        else:
            key = command.get("key")
            if op == "put":
                result = compute(copy.deepcopy(command["input"]))
                # The string API is part of the compute/present pipeline; parse it
                # back to retain the algorithm's original JSON scalar/list value.
                value = json.loads(present(result))
                state[key] = copy.deepcopy(value)
                event = {"ok": copy.deepcopy(value)}
            elif op == "get":
                event = {"ok": copy.deepcopy(state[key])} if key in state else {"error": "missing"}
            elif op == "delete":
                event = {"ok": copy.deepcopy(state.pop(key))} if key in state else {"error": "missing"}
            elif op == "expect":
                event = {"ok": True} if key in state and state[key] == command["value"] else {"error": "expectation"}
            elif op == "list":
                event = {"ok": [[name, copy.deepcopy(state[name])] for name in sorted(state)]}
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

        events.append(copy.deepcopy(event))
        if supplied_id is not _MISSING and "ok" in event:
            cache[supplied_id] = (copy.deepcopy(identity), copy.deepcopy(event))

    output_state = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return _event_json({"events": events, "state": output_state, "depth": len(stack)})
