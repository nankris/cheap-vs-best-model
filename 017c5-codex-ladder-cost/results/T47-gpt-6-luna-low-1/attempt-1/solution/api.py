import json

from render import present
from service import compute


def run(payload):
    inputs = json.loads(payload)
    return json.dumps([json.loads(present(compute(rows))) for rows in inputs])
