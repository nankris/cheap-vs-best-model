import json

import render
import service


def run(payload: str) -> str:
    rows_list = json.loads(payload)
    outputs = [render.present(service.compute(rows)) for rows in rows_list]
    return "[" + ", ".join(outputs) + "]"
