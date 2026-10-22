"""Public immutable result model."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Result:
    value: Optional[int]
