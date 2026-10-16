import json

from render import present
from service import compute


def run(payload):
    rows = json.loads(payload)
    return present(compute(rows))
