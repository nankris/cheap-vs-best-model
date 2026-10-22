"""Per-invocation transactional journal with successful-event idempotency."""

from copy import deepcopy
import json

from service import compute
from render import present


_REQUIRED = {
    "put": ("key", "input"),
    "get": ("key",),
    "delete": ("key",),
    "expect": ("key", "value"),
    "begin": (),
    "commit": (),
    "rollback": (),
    "list": (),
}


def _listing(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def run(payload: str) -> str:
    state = {}
    stack = []
    cache = {}
    events = []

    def execute(command):
        nonlocal state
        if not isinstance(command, dict):
            return {"error": "command"}

        has_id = "id" in command
        command_id = command.get("id")
        if has_id and not isinstance(command_id, str):
            return {"error": "command"}

        identity = {key: value for key, value in command.items() if key != "id"}
        if has_id and command_id in cache:
            original, event = cache[command_id]
            if identity == original:
                return deepcopy(event)
            return {"error": "id-conflict"}

        op = command.get("op")
        if not isinstance(op, str) or op not in _REQUIRED:
            return {"error": "command"}
        required = _REQUIRED[op]
        if any(field not in command for field in required):
            return {"error": "command"}
        if "key" in required and not isinstance(command["key"], str):
            return {"error": "command"}

        if op == "put":
            value = json.loads(present(compute(deepcopy(command["input"]))))
            state[command["key"]] = deepcopy(value)
            event = {"ok": deepcopy(value)}
        elif op in ("get", "delete"):
            key = command["key"]
            if key not in state:
                return {"error": "missing"}
            event = {"ok": deepcopy(state[key])}
            if op == "delete":
                del state[key]
        elif op == "expect":
            key = command["key"]
            if key not in state or state[key] != command["value"]:
                return {"error": "expectation"}
            event = {"ok": True}
        elif op == "list":
            event = {"ok": _listing(state)}
        elif op == "begin":
            stack.append(deepcopy(state))
            event = {"ok": len(stack)}
        else:
            if not stack:
                return {"error": "transaction"}
            snapshot = stack.pop()
            if op == "rollback":
                state = deepcopy(snapshot)
            event = {"ok": len(stack)}

        if has_id:
            cache[command_id] = (deepcopy(identity), deepcopy(event))
        return event

    for command in json.loads(payload):
        events.append(deepcopy(execute(command)))

    return json.dumps({"events": events, "state": _listing(state), "depth": len(stack)})
