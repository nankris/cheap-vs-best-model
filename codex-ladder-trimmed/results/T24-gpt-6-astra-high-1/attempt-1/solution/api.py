from copy import deepcopy
import json

from service import compute
from render import present


_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}
_KEY_OPS = {"put", "get", "delete", "expect"}


def _listed(state):
    return deepcopy([[key, state[key]] for key in sorted(state)])


def _execute(command, state, snapshots):
    """Validate the whole control command before changing journal state."""
    op = command.get("op")
    if not isinstance(op, str) or op not in _OPS:
        return {"error": "command"}
    if op in _KEY_OPS and not isinstance(command.get("key"), str):
        return {"error": "command"}
    if op == "put" and "input" not in command:
        return {"error": "command"}
    if op == "expect" and "value" not in command:
        return {"error": "command"}

    if op == "put":
        value = json.loads(present(compute(deepcopy(command["input"]))))
        state[command["key"]] = deepcopy(value)
        return {"ok": deepcopy(value)}
    if op in {"get", "delete"}:
        key = command["key"]
        if key not in state:
            return {"error": "missing"}
        value = state[key] if op == "get" else state.pop(key)
        return {"ok": deepcopy(value)}
    if op == "expect":
        key = command["key"]
        if key in state and state[key] == command["value"]:
            return {"ok": True}
        return {"error": "expectation"}
    if op == "list":
        return {"ok": _listed(state)}
    if op == "begin":
        snapshots.append(deepcopy(state))
        return {"ok": len(snapshots)}
    if not snapshots:
        return {"error": "transaction"}
    snapshot = snapshots.pop()
    if op == "rollback":
        state.clear()
        state.update(deepcopy(snapshot))
    return {"ok": len(snapshots)}


def run(payload: str) -> str:
    commands = json.loads(payload)
    state = {}
    snapshots = []
    cache = {}
    events = []
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
            cached_identity, cached_event = cache[command_id]
            if identity == cached_identity:
                events.append(deepcopy(cached_event))
            else:
                events.append({"error": "id-conflict"})
            continue
        event = _execute(command, state, snapshots)
        if has_id and "ok" in event:
            cache[command_id] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))
    return json.dumps({"events": events, "state": _listed(state), "depth": len(snapshots)})
