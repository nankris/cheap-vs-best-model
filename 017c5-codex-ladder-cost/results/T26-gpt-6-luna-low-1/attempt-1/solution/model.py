from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    """The algorithm's result value."""

    value: Any
