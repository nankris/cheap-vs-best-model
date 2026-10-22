"""A per-invocation transactional journal with successful-event replay."""

from copy import deepcopy
import json

from service import compute
from render import present


_OPS = {"put", "get", "delete", "begin", "commit", "rollback", "expect", "list"}
_KEY_OPS = {"put", "get", "delete", "expect"}


def _listing(state):
    return [[key, deepcopy(state[key])] for key in sorted(state)]


class _Journal:
    def __init__(self):
        self.state = {}
        self.stack = []
        self.cache = {}

    def command(self, command):
        if not isinstance(command, dict):
            return {"error": "command"}

        has_id = "id" in command
        identity = None
        if has_id:
            identifier = command["id"]
            if not isinstance(identifier, str):
                return {"error": "command"}
            identity = {key: value for key, value in command.items() if key != "id"}
            if identifier in self.cache:
                original_identity, original_event = self.cache[identifier]
                if identity == original_identity:
                    return deepcopy(original_event)
                return {"error": "id-conflict"}

        op = command.get("op")
        if not isinstance(op, str) or op not in _OPS:
            return {"error": "command"}
        if op in _KEY_OPS and not isinstance(command.get("key"), str):
            return {"error": "command"}
        if op == "put" and "input" not in command:
            return {"error": "command"}
        if op == "expect" and "value" not in command:
            return {"error": "command"}

        event = self._execute(op, command)
        if has_id and "ok" in event:
            self.cache[identifier] = (deepcopy(identity), deepcopy(event))
        return event

    def _execute(self, op, command):
        if op == "put":
            value = json.loads(present(compute(deepcopy(command["input"]))))
            self.state[command["key"]] = deepcopy(value)
            return {"ok": value}
        if op in {"get", "delete"}:
            key = command["key"]
            if key not in self.state:
                return {"error": "missing"}
            value = deepcopy(self.state[key])
            if op == "delete":
                del self.state[key]
            return {"ok": value}
        if op == "begin":
            self.stack.append(deepcopy(self.state))
            return {"ok": len(self.stack)}
        if op in {"commit", "rollback"}:
            if not self.stack:
                return {"error": "transaction"}
            snapshot = self.stack.pop()
            if op == "rollback":
                self.state = snapshot
            return {"ok": len(self.stack)}
        if op == "expect":
            key = command["key"]
            if key in self.state and self.state[key] == command["value"]:
                return {"ok": True}
            return {"error": "expectation"}
        return {"ok": _listing(self.state)}


def run(payload: str) -> str:
    journal = _Journal()
    events = [journal.command(command) for command in json.loads(payload)]
    return json.dumps({
        "events": events,
        "state": _listing(journal.state),
        "depth": len(journal.stack),
    })
