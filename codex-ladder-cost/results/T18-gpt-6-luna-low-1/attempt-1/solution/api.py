"""JSON API for the transactional command journal."""

import copy
import json

from render import present
from service import compute


_MISSING = object()


def _event_error(name):
    return {"error": name}


def run(payload: str) -> str:
    """Run one independent journal invocation from a JSON command list."""
    commands = json.loads(payload)
    if not isinstance(commands, list):
        raise ValueError("journal input must be a list")

    state = {}
    snapshots = []
    cache = {}
    events = []

    for command in commands:
        if not isinstance(command, dict):
            events.append(_event_error("command"))
            continue

        supplied_id = command.get("id", _MISSING)
        if supplied_id is not _MISSING and not isinstance(supplied_id, str):
            events.append(_event_error("command"))
            continue

        if isinstance(supplied_id, str):
            identity = {key: value for key, value in command.items() if key != "id"}
            if supplied_id in cache:
                prior_identity, prior_event = cache[supplied_id]
                if identity == prior_identity:
                    events.append(copy.deepcopy(prior_event))
                else:
                    events.append(_event_error("id-conflict"))
                continue

        op = command.get("op", _MISSING)
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
            event = _event_error("command")
        elif any(field not in command for field in required[op]):
            event = _event_error("command")
        elif any(
            field == "key" and not isinstance(command[field], str)
            for field in required[op]
        ):
            event = _event_error("command")
        else:
            key = command.get("key")
            if op == "put":
                result = compute(command["input"])
                # The Result's field is JSON data; render via the public pipeline,
                # then parse it so the journal owns a fresh mutable value.
                value = json.loads(present(result))
                state[key] = copy.deepcopy(value)
                event = {"ok": copy.deepcopy(value)}
            elif op == "get":
                if key not in state:
                    event = _event_error("missing")
                else:
                    event = {"ok": copy.deepcopy(state[key])}
            elif op == "delete":
                if key not in state:
                    event = _event_error("missing")
                else:
                    old = state.pop(key)
                    event = {"ok": copy.deepcopy(old)}
            elif op == "begin":
                snapshots.append(copy.deepcopy(state))
                event = {"ok": len(snapshots)}
            elif op == "commit":
                if not snapshots:
                    event = _event_error("transaction")
                else:
                    snapshots.pop()
                    event = {"ok": len(snapshots)}
            elif op == "rollback":
                if not snapshots:
                    event = _event_error("transaction")
                else:
                    state = snapshots.pop()
                    event = {"ok": len(snapshots)}
            elif op == "expect":
                if key in state and state[key] == command["value"]:
                    event = {"ok": True}
                else:
                    event = _event_error("expectation")
            else:  # list
                event = {"ok": [[k, copy.deepcopy(state[k])] for k in sorted(state)]}

        if isinstance(supplied_id, str) and "ok" in event:
            cache[supplied_id] = (
                copy.deepcopy({key: value for key, value in command.items() if key != "id"}),
                copy.deepcopy(event),
            )
        events.append(copy.deepcopy(event))

    output_state = [[key, copy.deepcopy(state[key])] for key in sorted(state)]
    return json.dumps(
        {"events": events, "state": output_state, "depth": len(snapshots)},
        ensure_ascii=True,
    )
