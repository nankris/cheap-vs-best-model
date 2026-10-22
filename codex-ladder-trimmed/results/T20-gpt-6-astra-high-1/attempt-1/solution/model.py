"""Shared result type for the algorithm pipeline."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    value: Any
