import json


def decode(payload):
    """Decode the JSON list of directed [before, after] pairs."""
    return json.loads(payload)
