import json

from codec import decode
from service import compute
from render import present


def run(payload: str) -> str:
    return json.dumps(present(compute(decode(payload))))
