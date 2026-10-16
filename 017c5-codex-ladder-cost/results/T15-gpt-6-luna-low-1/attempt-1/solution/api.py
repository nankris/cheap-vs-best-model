import copy
import json

from service import compute


_MISSING = object()


def _valid_command(command):
    if not isinstance(command, dict):
        return None
    op = command.get("op", _MISSING)
    if not isinstance(op, str) or op not in {
        "put", "get", "delete", "begin", "commit", "rollback", "expect", "list"
    }:
        return None
    if "id" in command and not isinstance(command["id"], str):
        return None
    if op in {"put", "get", "delete", "expect"}:
        if "key" not in command or not isinstance(command["key"], str):
            return None
    if op == "put" and "input" not in command:
        return None
    if op == "expect" and "value" not in command:
        return None
    return op


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise TypeError("journal input must be a list")

    state = {}
    snapshots = []
    cache = {}
    events = []

    for command in commands:
        # A valid string id is looked up before validating any other fields.
        if isinstance(command, dict) and isinstance(command.get("id", _MISSING), str):
            command_id = command["id"]
            identity = _identity(command)
            if command_id in cache:
                cached_identity, cached_event = cache[command_id]
                if identity == cached_identity:
                    events.append(copy.deepcopy(cached_event))
                else:
                    events.append({"error": "id-conflict"})
                continue
        else:
            command_id = None

        op = _valid_command(command)
        if op is None:
            event = {"error": "command"}
        elif op == "put":
            result = compute(command["input"])
            value = copy.deepcopy(result.value)
            state[command["key"]] = copy.deepcopy(value)
            event = {"ok": copy.deepcopy(value)}
        elif op == "get":
            key = command["key"]
            if key in state:
                event = {"ok": copy.deepcopy(state[key])}
            else:
                event = {"error": "missing"}
        elif op == "delete":
            key = command["key"]
            if key in state:
                event = {"ok": copy.deepcopy(state.pop(key))}
            else:
                event = {"error": "missing"}
        elif op == "begin":
            snapshots.append(copy.deepcopy(state))
            event = {"ok": len(snapshots)}
        elif op == "commit":
            if snapshots:
                snapshots.pop()
                event = {"ok": len(snapshots)}
            else:
                event = {"error": "transaction"}
        elif op == "rollback":
            if snapshots:
                state = snapshots.pop()
                event = {"ok": len(snapshots)}
            else:
                event = {"error": "transaction"}
        elif op == "expect":
            key = command["key"]
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = {"error": "expectation"}
        else:  # list
            event = {"ok": copy.deepcopy([[key, state[key]] for key in sorted(state)])}

        events.append(copy.deepcopy(event))
        if command_id is not None and "ok" in event:
            cache[command_id] = (copy.deepcopy(identity), copy.deepcopy(event))

    return json.dumps(
        {
            "events": events,
            "state": [[key, copy.deepcopy(state[key])] for key in sorted(state)],
            "depth": len(snapshots),
        },
        ensure_ascii=False,
    )
