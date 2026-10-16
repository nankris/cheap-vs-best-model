import json


def decode(payload):
    values = json.loads(payload)
    if not isinstance(values, list) or any(type(value) is not int for value in values):
        raise ValueError("payload must be a JSON list of integers")
    return values
