import json

from service import compute
from render import present


def run(payload):
    inputs = json.loads(payload)
    return json.dumps([json.loads(present(compute([row])))[0] for row in inputs])
