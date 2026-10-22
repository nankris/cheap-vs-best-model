import json

from service import compute
from render import present


def run(payload):
    """Run the processing pipeline for every input in a JSON list."""
    inputs = json.loads(payload)
    return json.dumps([json.loads(present(compute(rows))) for rows in inputs])
