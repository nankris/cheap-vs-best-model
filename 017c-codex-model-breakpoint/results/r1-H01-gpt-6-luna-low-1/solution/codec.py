import json

def decode(payload):
    """Decode a JSON array of integer intervals."""
    return json.loads(payload)
