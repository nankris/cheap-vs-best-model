import json

from service import compute
from render import present


def run(payload: str) -> str:
    inputs = json.loads(payload)
    return "[" + ", ".join(present(compute(rows)) for rows in inputs) + "]"
