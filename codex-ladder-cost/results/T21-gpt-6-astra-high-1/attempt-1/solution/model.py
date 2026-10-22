"""Shared result type for algorithm computation and rendering."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    value: Any
