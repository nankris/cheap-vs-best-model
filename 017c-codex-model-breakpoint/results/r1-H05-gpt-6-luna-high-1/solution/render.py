import json


def present(value):
    return json.dumps(value, separators=(",", ":"))
