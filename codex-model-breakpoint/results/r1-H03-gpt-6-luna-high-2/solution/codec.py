"""JSON input decoding for the public API."""

import json


def decode(payload):
    return json.loads(payload)
