import copy
import json

from service import compute
from render import present


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

    state = {}
    stack = []
    cache = {}
    events = []
    missing = object()

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue

        supplied_id = command.get("id", missing)
        if supplied_id is not missing and not isinstance(supplied_id, str):
            events.append({"error": "command"})
            continue

        if isinstance(supplied_id, str):
            identity = {key: value for key, value in command.items() if key != "id"}
            if supplied_id in cache:
                prior_identity, prior_event = cache[supplied_id]
                if identity == prior_identity:
                    events.append(copy.deepcopy(prior_event))
                else:
                    events.append({"error": "id-conflict"})
                continue

        op = command.get("op", missing)
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
        if op not in required or any(field not in command for field in required[op]):
            event = {"error": "command"}
        elif any("key" in required[op] and not isinstance(command["key"], str) for _ in (0,)):
            event = {"error": "command"}
        elif op == "put":
            result = compute(command["input"])
            # Exercise the public render pipeline; parse its JSON representation
            # back into a journal-owned value.
            value = json.loads(present(result))
            state[command["key"]] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            key = command["key"]
            event = {"ok": copy.deepcopy(state[key])} if key in state else {"error": "missing"}
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
            event = {"ok": True} if key in state and state[key] == command["value"] else {"error": "expectation"}
        else:  # list
            event = {"ok": copy.deepcopy(sorted(state.items()))}

        if isinstance(supplied_id, str) and "ok" in event:
            cache[supplied_id] = (copy.deepcopy(identity), copy.deepcopy(event))
        events.append(event)

    output_state = [[key, copy.deepcopy(value)] for key, value in sorted(state.items())]
    return json.dumps({"events": events, "state": output_state, "depth": len(stack)}, ensure_ascii=True)
