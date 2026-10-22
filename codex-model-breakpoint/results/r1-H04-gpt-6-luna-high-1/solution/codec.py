import json


def decode(payload):
    """Decode the JSON edge rows and final source/target row."""
    return json.loads(payload)
