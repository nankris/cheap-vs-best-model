from typing import Iterable

from core import Money, solve


def compute(rows: Iterable[str]) -> Money:
    return solve(rows)
