import copy
import json

from service import compute
from render import present


def _is_command_error(command):
    if not isinstance(command, dict):
        return True
    if "id" in command and not isinstance(command["id"], str):
        return True
    op = command.get("op")
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
    if not isinstance(op, str) or op not in required:
        return True
    if any(field not in command for field in required[op]):
        return True
    if "key" in required[op] and not isinstance(command["key"], str):
        return True
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
        if isinstance(command, dict) and isinstance(command.get("id"), str):
            command_id = command["id"]
            identity = {k: v for k, v in command.items() if k != "id"}
            if command_id in cache:
                cached_identity, cached_event = cache[command_id]
                if identity == cached_identity:
                    events.append(copy.deepcopy(cached_event))
                else:
                    events.append({"error": "id-conflict"})
                continue
        else:
            command_id = None
            identity = None

        if _is_command_error(command):
            event = {"error": "command"}
        else:
            op = command["op"]
            if op == "put":
                # compute/present form the public algorithm pipeline; the
                # resulting JSON string is decoded to the stored JSON value.
                value = json.loads(present(compute(command["input"])))
                state[command["key"]] = copy.deepcopy(value)
                event = {"ok": copy.deepcopy(value)}
            elif op == "get":
                key = command["key"]
                event = {"ok": copy.deepcopy(state[key])} if key in state else {"error": "missing"}
            elif op == "delete":
                key = command["key"]
                event = {"ok": copy.deepcopy(state.pop(key))} if key in state else {"error": "missing"}
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
            else:  # list
                event = {"ok": [[k, copy.deepcopy(state[k])] for k in sorted(state)]}

        if command_id is not None and "ok" in event:
            cache[command_id] = (copy.deepcopy(identity), copy.deepcopy(event))
        events.append(copy.deepcopy(event))

    output = {"events": events,
              "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
              "depth": len(stack)}
    return json.dumps(output, ensure_ascii=True)
