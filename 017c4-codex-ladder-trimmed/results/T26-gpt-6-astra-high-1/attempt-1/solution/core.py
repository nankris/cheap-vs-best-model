"""Stable SemVer 2.0.0 precedence sorting."""


def _numeric_key(identifier):
    # Valid SemVer numbers have no leading zeros. Comparing length and digits
    # gives integer order without imposing a limit on the number of digits.
    return len(identifier), identifier


def _precedence(version):
    public = version.split("+", 1)[0]
    core, separator, prerelease = public.partition("-")
    numbers = tuple(_numeric_key(part) for part in core.split("."))
    if not separator:
        return numbers, 1, ()
    identifiers = tuple(
        (0, _numeric_key(part)) if part.isdigit() else (1, part)
        for part in prerelease.split(".")
    )
    return numbers, 0, identifiers


def solve(rows):
    return sorted(rows, key=_precedence)
