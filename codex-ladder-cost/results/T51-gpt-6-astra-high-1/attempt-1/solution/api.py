import json

from service import compute
from render import present


def run(payload: str) -> str:
    return "[" + ", ".join(
        present(compute(rows)) for rows in json.loads(payload)
    ) + "]"
