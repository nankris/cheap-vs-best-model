import json

from service import compute
from render import present


def run(payload: str) -> str:
    return present(compute(json.loads(payload)))
