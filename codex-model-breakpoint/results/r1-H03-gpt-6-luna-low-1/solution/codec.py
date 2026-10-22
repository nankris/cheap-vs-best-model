import json


def decode(payload):
    """Decode a JSON payload containing ledger rows."""
    return json.loads(payload)
