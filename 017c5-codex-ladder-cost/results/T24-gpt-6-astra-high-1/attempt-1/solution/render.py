"""Serialize computation results without changing their shape."""

import json
from model import Result


def present(result: Result) -> str:
    return json.dumps(result.value)
