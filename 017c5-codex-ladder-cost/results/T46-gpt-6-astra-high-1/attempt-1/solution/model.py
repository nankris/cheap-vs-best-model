"""Public result model."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class Result:
    value: Optional[List[str]]
