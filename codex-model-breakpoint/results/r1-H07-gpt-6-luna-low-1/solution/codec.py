import json


def decode(payload):
    """Decode the JSON array of undirected [node, node] edges."""
    return json.loads(payload)
