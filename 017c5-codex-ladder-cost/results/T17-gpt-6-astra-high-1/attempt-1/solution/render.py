"""Serialize a computation result without changing its JSON shape."""

import json
from model import Result


def present(result: Result) -> str:
    return json.dumps(result.value)
