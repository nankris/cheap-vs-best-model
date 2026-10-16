import json


def decode(payload):
    """Decode the JSON request containing edges and a final query row."""
    return json.loads(payload)
