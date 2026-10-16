import json
def decode(payload):
    """Decode a JSON list payload into Python values."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("payload must be a JSON list")
    return rows
