import json


def decode(payload):
    """Decode the JSON request body into its operation rows."""
    return json.loads(payload)
