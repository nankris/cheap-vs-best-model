import json

import render
import service


def run(payload: str) -> str:
    return "[" + ", ".join(
        render.present(service.compute(rows)) for rows in json.loads(payload)
    ) + "]"
