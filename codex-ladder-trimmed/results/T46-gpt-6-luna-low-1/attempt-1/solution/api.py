import json

from render import present
from service import compute


def run(payload: str) -> str:
    inputs = json.loads(payload)
    outputs = [present(compute(rows)).strip() for rows in inputs]
    return json.dumps([json.loads(output) for output in outputs])
