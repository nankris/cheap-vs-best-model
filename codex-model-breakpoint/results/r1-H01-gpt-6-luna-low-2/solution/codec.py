import json


def decode(payload):
    """Decode the JSON payload into its interval rows."""
    return json.loads(payload)
