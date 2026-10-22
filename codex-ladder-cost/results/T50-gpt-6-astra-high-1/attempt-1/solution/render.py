"""JSON presentation of a result."""

import json


def present(result):
    return json.dumps(result.value)
