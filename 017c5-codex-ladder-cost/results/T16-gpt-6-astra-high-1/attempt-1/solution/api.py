"""A per-invocation journal with savepoints and successful-event replay."""

from copy import deepcopy
import json

from service import compute
from render import present


def run(payload: str) -> str:
    commands = json.loads(payload)
    state = {}
    stack = []
    cache = {}
    events = []

    def execute(command):
        nonlocal state

        op = command.get("op")
        if op not in ("put", "get", "delete", "begin", "commit",
                      "rollback", "expect", "list"):
            return {"error": "command"}
        if op in ("put", "get", "delete", "expect"):
            if "key" not in command or not isinstance(command["key"], str):
                return {"error": "command"}
            key = command["key"]
        if op == "put" and "input" not in command:
            return {"error": "command"}
        if op == "expect" and "value" not in command:
            return {"error": "command"}

        if op == "put":
            value = json.loads(present(compute(deepcopy(command["input"]))))
            state[key] = deepcopy(value)
            return {"ok": deepcopy(value)}
        if op in ("get", "delete"):
            if key not in state:
                return {"error": "missing"}
            value = state.pop(key) if op == "delete" else state[key]
            return {"ok": deepcopy(value)}
        if op == "expect":
            if key in state and state[key] == command["value"]:
                return {"ok": True}
            return {"error": "expectation"}
        if op == "list":
            return {"ok": [[key, deepcopy(state[key])] for key in sorted(state)]}
        if op == "begin":
            stack.append(deepcopy(state))
            return {"ok": len(stack)}
        if not stack:
            return {"error": "transaction"}
        if op == "rollback":
            state = stack.pop()
        else:  # commit
            stack.pop()
        return {"ok": len(stack)}

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue
        has_id = "id" in command
        if has_id and not isinstance(command["id"], str):
            events.append({"error": "command"})
            continue

        if has_id:
            identity = {key: value for key, value in command.items() if key != "id"}
            command_id = command["id"]
            if command_id in cache:
                original_identity, original_event = cache[command_id]
                if identity == original_identity:
                    events.append(deepcopy(original_event))
                else:
                    events.append({"error": "id-conflict"})
                continue

        event = execute(command)
        if has_id and "ok" in event:
            cache[command_id] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({
        "events": events,
        "state": [[key, deepcopy(state[key])] for key in sorted(state)],
        "depth": len(stack),
    })
