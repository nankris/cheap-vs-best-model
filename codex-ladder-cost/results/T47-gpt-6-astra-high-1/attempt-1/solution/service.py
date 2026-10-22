"""Wrap the algorithm's output in its public result model."""

import core
from model import Result


def compute(rows):
    return Result(core.solve(rows))
