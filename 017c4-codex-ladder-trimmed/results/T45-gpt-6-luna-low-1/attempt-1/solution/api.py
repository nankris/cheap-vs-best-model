from service import compute
from render import present
import json


def run(payload: str) -> str:
    inputs = json.loads(payload)
    return json.dumps([compute(rows).value for rows in inputs])
