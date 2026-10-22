import json


def decode(payload):
    """Decode the JSON edge list supplied to the public API."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("payload must be a JSON array of edges")
    return rows
