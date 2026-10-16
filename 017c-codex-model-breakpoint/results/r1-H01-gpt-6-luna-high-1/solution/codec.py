import json


def decode(payload):
    """Decode the JSON payload containing closed integer intervals."""
    return json.loads(payload)
