import json


def decode(payload):
    """Decode the JSON array of undirected edges."""
    return json.loads(payload)
