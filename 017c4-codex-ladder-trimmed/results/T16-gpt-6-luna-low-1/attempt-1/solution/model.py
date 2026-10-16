from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    """A computed algorithm result."""

    value: Any
