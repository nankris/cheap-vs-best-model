"""Wrap algorithm results in the shared result type."""

import core
from model import Result


def compute(rows):
    return Result(core.solve(rows))
