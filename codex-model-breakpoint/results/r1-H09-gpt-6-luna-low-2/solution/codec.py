import json


def decode(payload):
    data = json.loads(payload)
    if not isinstance(data, list) or any(not isinstance(row, str) for row in data):
        raise ValueError("payload must be a JSON array of decimal strings")
    return data
