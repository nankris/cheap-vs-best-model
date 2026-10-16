import json

import render
import service


def run(payload: str) -> str:
    rows = json.loads(payload)
    return "[" + ", ".join(render.present(service.compute(row)) for row in rows) + "]"
