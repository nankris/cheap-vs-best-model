"""Serialize a computation result as JSON."""

import json
from model import Result


def present(result: Result):
    return json.dumps(result.value, ensure_ascii=False)
