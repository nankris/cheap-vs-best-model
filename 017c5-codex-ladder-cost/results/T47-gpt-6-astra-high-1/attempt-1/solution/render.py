"""JSON rendering for results."""

import json


def present(result):
    return json.dumps(result.value)
