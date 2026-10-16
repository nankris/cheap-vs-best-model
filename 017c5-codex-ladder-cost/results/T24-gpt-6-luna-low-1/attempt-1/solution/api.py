import json
from copy import deepcopy

from service import compute
from render import present


def _identity(command):
    return {key: value for key, value in command.items() if key != "id"}


def _is_success(event):
    return "ok" in event


def run(payload: str) -> str:
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

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
        # A supplied id must be a string, including when it is explicitly null.
        if has_id and not isinstance(command_id, str):
            events.append({"error": "command"})
            continue

        identity = _identity(command)
        if has_id and command_id in cache:
            prior_identity, prior_event = cache[command_id]
            if identity == prior_identity:
                events.append(deepcopy(prior_event))
            else:
                events.append({"error": "id-conflict"})
            continue

        op = command.get("op")
        event = None

        if op == "put":
            if "key" not in command or "input" not in command or not isinstance(command["key"], str):
                event = {"error": "command"}
            else:
                value = json.loads(present(compute(command["input"])))
                state[command["key"]] = deepcopy(value)
                event = {"ok": deepcopy(value)}
        elif op == "get":
            if "key" not in command or not isinstance(command["key"], str):
                event = {"error": "command"}
            elif command["key"] in state:
                event = {"ok": deepcopy(state[command["key"]])}
            else:
                event = {"error": "missing"}
        elif op == "delete":
            if "key" not in command or not isinstance(command["key"], str):
                event = {"error": "command"}
            elif command["key"] in state:
                event = {"ok": deepcopy(state.pop(command["key"]))}
            else:
                event = {"error": "missing"}
        elif op == "begin":
            snapshots.append(deepcopy(state))
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
            if "key" not in command or "value" not in command or not isinstance(command["key"], str):
                event = {"error": "command"}
            else:
                event = {"ok": True} if command["key"] in state and state[command["key"]] == command["value"] else {"error": "expectation"}
        elif op == "list":
            event = {"ok": [[key, deepcopy(state[key])] for key in sorted(state)]}
        else:
            event = {"error": "command"}

        events.append(event)
        if has_id and _is_success(event):
            cache[command_id] = (deepcopy(identity), deepcopy(event))

    output = {
        "events": events,
        "state": [[key, deepcopy(state[key])] for key in sorted(state)],
        "depth": len(snapshots),
    }
    return json.dumps(output, ensure_ascii=False)
