from service import compute
from render import present
import json


def run(payload):
    inputs = json.loads(payload)
    return json.dumps([json.loads(present(compute(rows))) for rows in inputs])
