"""JSON input decoding for the row operation API."""

import json


def decode(payload):
    """Decode a JSON payload into its operation list."""
    return json.loads(payload)
