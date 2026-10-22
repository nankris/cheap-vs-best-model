from core import solve
from model import Result


def compute(rows):
    return Result(solve(rows))
