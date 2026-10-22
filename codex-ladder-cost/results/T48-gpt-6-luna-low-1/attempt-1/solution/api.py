import json

from render import present
from service import compute


def run(payload: str) -> str:
    inputs = json.loads(payload)
    outputs = [json.loads(present(compute(rows))) for rows in inputs]
    return json.dumps(outputs)
