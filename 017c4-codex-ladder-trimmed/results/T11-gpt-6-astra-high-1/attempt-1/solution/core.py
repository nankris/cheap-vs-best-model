"""Stable SemVer 2.0.0 precedence ordering."""


def _number_key(digits):
    # Valid SemVer numbers have no leading zeroes. Comparing length first
    # gives integer ordering without a limit on the number of digits.
    return len(digits), digits


def _precedence(version):
    without_build = version.split("+", 1)[0]
    core, separator, prerelease = without_build.partition("-")
    core_key = tuple(_number_key(part) for part in core.split("."))
    identifiers = tuple(
        (0, _number_key(part)) if part.isdigit() else (1, part)
        for part in prerelease.split(".")
    ) if separator else ()
    return core_key, not bool(separator), identifiers


def solve(rows):
    """Return original version strings in stable ascending precedence order."""
    return sorted(rows, key=_precedence)
