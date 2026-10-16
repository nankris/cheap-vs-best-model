"""A per-invocation journal with nested savepoints and idempotency."""

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

    def listing():
        return [[key, deepcopy(state[key])] for key in sorted(state)]

    def execute(command):
        op = command.get("op")
        if op not in ("put", "get", "delete", "begin", "commit", "rollback",
                      "expect", "list"):
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
        if op == "get":
            if key not in state:
                return {"error": "missing"}
            return {"ok": deepcopy(state[key])}
        if op == "delete":
            if key not in state:
                return {"error": "missing"}
            return {"ok": deepcopy(state.pop(key))}
        if op == "expect":
            if key in state and state[key] == command["value"]:
                return {"ok": True}
            return {"error": "expectation"}
        if op == "list":
            return {"ok": listing()}
        if op == "begin":
            stack.append(deepcopy(state))
            return {"ok": len(stack)}
        if not stack:
            return {"error": "transaction"}
        snapshot = stack.pop()
        if op == "rollback":
            state.clear()
            state.update(deepcopy(snapshot))
        return {"ok": len(stack)}

    for command in commands:
        if not isinstance(command, dict):
            events.append({"error": "command"})
            continue
        has_id = "id" in command
        command_id = command.get("id")
        if has_id and not isinstance(command_id, str):
            events.append({"error": "command"})
            continue
        identity = {key: value for key, value in command.items() if key != "id"}
        if has_id and command_id in cache:
            original_identity, original_event = cache[command_id]
            if identity == original_identity:
                events.append(deepcopy(original_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        event = execute(command)
        if has_id and "ok" in event:
            cache[command_id] = deepcopy(identity), deepcopy(event)
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": listing(), "depth": len(stack)})
