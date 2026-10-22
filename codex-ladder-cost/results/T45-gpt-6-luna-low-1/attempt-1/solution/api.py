import json

from service import compute
from render import present


def run(payload: str) -> str:
    inputs = json.loads(payload)
    outputs = [json.loads(present(compute(rows))) for rows in inputs]
    return json.dumps(outputs)
