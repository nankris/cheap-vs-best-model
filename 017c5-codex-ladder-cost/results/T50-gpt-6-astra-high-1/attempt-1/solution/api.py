"""Batch JSON entry point."""

import json

import render
import service


def run(payload: str) -> str:
    inputs = json.loads(payload)
    return "[" + ", ".join(
        render.present(service.compute(rows)) for rows in inputs
    ) + "]"
