"""JSON rendering for public results."""

import json


def present(result):
    return json.dumps(result.value)
