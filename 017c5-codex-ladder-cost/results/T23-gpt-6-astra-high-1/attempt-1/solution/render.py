"""Serialize the value carried by a computation result."""

import json

from model import Result


def present(result: Result):
    return json.dumps(result.value)
