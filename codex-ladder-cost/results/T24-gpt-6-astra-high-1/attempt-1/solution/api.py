"""JSON journal API with transactions and invocation-local idempotency."""

import json
from copy import deepcopy

from service import compute
from render import present


def _valid_command(command):
    op = command.get("op")
    if op not in ("put", "get", "delete", "begin", "commit", "rollback",
                  "expect", "list"):
        return False
    if op in ("put", "get", "delete", "expect"):
        if not isinstance(command.get("key"), str):
            return False
    if op == "put" and "input" not in command:
        return False
    if op == "expect" and "value" not in command:
        return False
    return True


def _state_rows(state):
    return deepcopy([[key, state[key]] for key in sorted(state)])


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
            original_identity, original_event = cache[command_id]
            if identity == original_identity:
                events.append(deepcopy(original_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        if not _valid_command(command):
            events.append({"error": "command"})
            continue

        op = command["op"]
        if op == "put":
            value = json.loads(present(compute(deepcopy(command["input"]))))
            state[command["key"]] = deepcopy(value)
            event = {"ok": deepcopy(value)}
        elif op in ("get", "delete"):
            key = command["key"]
            if key not in state:
                event = {"error": "missing"}
            else:
                event = {"ok": deepcopy(state[key])}
                if op == "delete":
                    del state[key]
        elif op == "begin":
            snapshots.append(deepcopy(state))
            event = {"ok": len(snapshots)}
        elif op == "commit" or op == "rollback":
            if not snapshots:
                event = {"error": "transaction"}
            else:
                snapshot = snapshots.pop()
                if op == "rollback":
                    state = snapshot
                event = {"ok": len(snapshots)}
        elif op == "expect":
            key = command["key"]
            if key in state and state[key] == command["value"]:
                event = {"ok": True}
            else:
                event = {"error": "expectation"}
        else:  # list
            event = {"ok": _state_rows(state)}

        if has_id and "ok" in event:
            cache[command_id] = (deepcopy(identity), deepcopy(event))
        events.append(deepcopy(event))

    return json.dumps({"events": events, "state": _state_rows(state),
                       "depth": len(snapshots)})
