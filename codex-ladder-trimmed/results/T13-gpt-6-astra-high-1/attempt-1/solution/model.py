from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    value: list[list[str]]
