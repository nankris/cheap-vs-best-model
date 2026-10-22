"""Wrap the algorithm's result in the public model."""

import core
from model import Result


def compute(rows):
    return Result(core.solve(rows))
