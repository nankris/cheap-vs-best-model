"""Wrap algorithm outputs in the shared result model."""

import core
from model import Result


def compute(rows):
    return Result(core.solve(rows))
