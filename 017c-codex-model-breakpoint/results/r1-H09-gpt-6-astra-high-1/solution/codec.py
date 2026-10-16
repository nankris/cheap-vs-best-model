import json


def decode(payload: str) -> list[str]:
    return json.loads(payload)
