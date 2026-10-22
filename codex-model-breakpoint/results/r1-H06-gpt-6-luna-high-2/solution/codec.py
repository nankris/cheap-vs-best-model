import json


def decode(payload):
    """Decode the JSON list of jobs supplied to the API."""
    return json.loads(payload)
