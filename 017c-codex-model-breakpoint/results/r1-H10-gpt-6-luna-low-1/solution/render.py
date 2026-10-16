import json


def present(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
