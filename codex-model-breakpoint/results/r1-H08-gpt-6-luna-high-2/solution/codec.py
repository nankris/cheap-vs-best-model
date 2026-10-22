import json


def decode(payload):
    """Decode a JSON array of interval rows."""
    return json.loads(payload)
