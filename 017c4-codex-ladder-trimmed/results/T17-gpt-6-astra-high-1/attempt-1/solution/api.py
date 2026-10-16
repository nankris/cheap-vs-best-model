from copy import deepcopy
import json

from service import compute
from render import present


_OPERATIONS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}
_KEY_OPERATIONS = {"put", "get", "delete", "expect"}


def _valid(command):
    op = command.get("op")
    if not isinstance(op, str) or op not in _OPERATIONS:
        return False
    if op in _KEY_OPERATIONS and not isinstance(command.get("key"), str):
        return False
    if op == "put" and "input" not in command:
        return False
    if op == "expect" and "value" not in command:
        return False
    return True


def _listed(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


def _execute(command, state, stack):
    op = command["op"]
    if op == "put":
        value = json.loads(present(compute(deepcopy(command["input"]))))
        state[command["key"]] = deepcopy(value)
        return {"ok": value}
    if op in {"get", "delete"}:
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        value = deepcopy(state[key])
        if op == "delete":
            del state[key]
        return {"ok": value}
    if op == "begin":
        stack.append(deepcopy(state))
        return {"ok": len(stack)}
    if op in {"commit", "rollback"}:
        if not stack:
            return {"error": "transaction"}
        snapshot = stack.pop()
        if op == "rollback":
            state.clear()
            state.update(deepcopy(snapshot))
        return {"ok": len(stack)}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    return {"ok": _listed(state)}


def run(payload: str) -> str:
    state = {}
    stack = []
    cache = {}
    events = []
    for command in json.loads(payload):
        if not isinstance(command, dict) or (
            "id" in command and not isinstance(command["id"], str)
        ):
            events.append({"error": "command"})
            continue

        has_id = "id" in command
        identity = {key: deepcopy(value) for key, value in command.items() if key != "id"}
        if has_id and command["id"] in cache:
            original_identity, original_event = cache[command["id"]]
            if identity == original_identity:
                events.append(deepcopy(original_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        if not _valid(command):
            events.append({"error": "command"})
            continue

        event = _execute(command, state, stack)
        if has_id and "ok" in event:
            cache[command["id"]] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _listed(state), "depth": len(stack)})
