import json


def decode(payload):
    """Decode the JSON payload into the directed edge rows."""
    return json.loads(payload)
