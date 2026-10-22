"""Shared result type for the computation and rendering pipeline."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    value: Any
