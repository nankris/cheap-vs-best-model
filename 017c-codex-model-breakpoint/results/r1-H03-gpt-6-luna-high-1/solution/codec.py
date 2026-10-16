import json


def decode(payload):
    """Decode the JSON request body into its transaction rows."""
    return json.loads(payload)
