"""Public result model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    value: int
