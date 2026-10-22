"""Serialize a result's value without changing its JSON shape."""

import json

from model import Result


def present(result: Result) -> str:
    return json.dumps(result.value)
