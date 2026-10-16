import json


def decode(payload):
    """Decode a JSON list payload."""
    return json.loads(payload)
