from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    """Immutable wrapper for an algorithm's JSON result."""

    value: Any
