import json


def decode(payload):
    """Decode the JSON array of job rows supplied to the public API."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("payload must be a JSON array")
    return rows
