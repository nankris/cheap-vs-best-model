"""SemVer precedence sorting for rows of version strings."""

import re
from functools import cmp_to_key


_VERSION = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _parse(version):
    match = _VERSION.fullmatch(version)
    if match is None:
        raise ValueError("invalid SemVer")
    major, minor, patch, prerelease = match.groups()
    if prerelease is not None:
        for identifier in prerelease.split("."):
            if identifier.isdigit() and len(identifier) > 1 and identifier[0] == "0":
                raise ValueError("numeric prerelease identifiers cannot have leading zeroes")
    return (int(major), int(minor), int(patch),
            None if prerelease is None else tuple(prerelease.split(".")))


def _compare_identifier(left, right):
    left_numeric, right_numeric = left.isdigit(), right.isdigit()
    if left_numeric and right_numeric:
        a, b = int(left), int(right)
        return (a > b) - (a < b)
    if left_numeric != right_numeric:
        return -1 if left_numeric else 1
    # SemVer's nonnumeric identifiers use ASCII lexical ordering.
    return (left > right) - (left < right)


def _compare_versions(left, right):
    a, b = left[1], right[1]
    for av, bv in zip(a[:3], b[:3]):
        if av != bv:
            return (av > bv) - (av < bv)
    ap, bp = a[3], b[3]
    if ap is None or bp is None:
        if ap is bp:
            return 0
        return 1 if ap is None else -1
    for ai, bi in zip(ap, bp):
        result = _compare_identifier(ai, bi)
        if result:
            return result
    return (len(ap) > len(bp)) - (len(ap) < len(bp))


def solve(rows):
    """Return a stable ascending precedence ordering of the input strings."""
    parsed = [(row, _parse(row)) for row in rows]
    parsed.sort(key=cmp_to_key(_compare_versions))
    return [row for row, _ in parsed]
