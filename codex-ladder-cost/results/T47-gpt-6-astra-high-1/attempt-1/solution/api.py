"""Batch JSON entry point."""

import json

import render
import service


def run(payload: str) -> str:
    inputs = json.loads(payload)
    # Each rendering is already a JSON value; assemble them into a JSON array.
    return "[" + ", ".join(
        render.present(service.compute(rows)) for rows in inputs
    ) + "]"
