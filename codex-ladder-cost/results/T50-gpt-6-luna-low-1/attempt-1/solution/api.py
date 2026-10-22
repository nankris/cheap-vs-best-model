import json

from render import present
from service import compute


def run(payload):
    inputs = json.loads(payload)
    return json.dumps([compute(rows).value for rows in inputs])
