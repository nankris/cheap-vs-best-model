"""Serialize the algorithm value, preserving its JSON type."""

import json
from model import Result


def present(result: Result) -> str:
    return json.dumps(result.value)
