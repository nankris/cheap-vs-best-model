import json


def decode(payload):
    """Decode the JSON payload containing directed [before, after] pairs."""
    return json.loads(payload)
