from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    """Immutable wrapper for a computed value."""

    value: object
