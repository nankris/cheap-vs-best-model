from copy import deepcopy
import json

from service import compute
from render import present


class _Journal:
    def __init__(self):
        self.state = {}
        self.stack = []
        self.cache = {}

    def apply(self, command):
        if not isinstance(command, dict):
            return {"error": "command"}

        has_id = "id" in command
        if has_id and not isinstance(command["id"], str):
            return {"error": "command"}

        identity = {key: value for key, value in command.items() if key != "id"}
        if has_id and command["id"] in self.cache:
            original, event = self.cache[command["id"]]
            if identity == original:
                return deepcopy(event)
            return {"error": "id-conflict"}

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
        op = command.get("op")
        if not isinstance(op, str) or op not in required:
            return {"error": "command"}
        if any(field not in command for field in required[op]):
            return {"error": "command"}
        if "key" in required[op] and not isinstance(command["key"], str):
            return {"error": "command"}

        # Capture identity before passing algorithm input through the pipeline.
        identity = deepcopy(identity)
        event = self._execute(op, command)
        if has_id and "ok" in event:
            self.cache[command["id"]] = (identity, deepcopy(event))
        return deepcopy(event)

    def _execute(self, op, command):
        if op == "put":
            value = json.loads(present(compute(deepcopy(command["input"]))))
            self.state[command["key"]] = deepcopy(value)
            return {"ok": value}
        if op in ("get", "delete"):
            key = command["key"]
            if key not in self.state:
                return {"error": "missing"}
            value = self.state.pop(key) if op == "delete" else self.state[key]
            return {"ok": deepcopy(value)}
        if op == "expect":
            key = command["key"]
            if key in self.state and self.state[key] == command["value"]:
                return {"ok": True}
            return {"error": "expectation"}
        if op == "list":
            return {"ok": self.entries()}
        if op == "begin":
            self.stack.append(deepcopy(self.state))
        else:
            if not self.stack:
                return {"error": "transaction"}
            snapshot = self.stack.pop()
            if op == "rollback":
                self.state = deepcopy(snapshot)
        return {"ok": len(self.stack)}

    def entries(self):
        return deepcopy([[key, self.state[key]] for key in sorted(self.state)])


def run(payload):
    journal = _Journal()
    events = [journal.apply(command) for command in json.loads(payload)]
    return json.dumps({
        "events": events,
        "state": journal.entries(),
        "depth": len(journal.stack),
    })
