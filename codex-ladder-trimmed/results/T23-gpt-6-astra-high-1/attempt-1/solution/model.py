"""Shared value returned by the computation service."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    value: Any
