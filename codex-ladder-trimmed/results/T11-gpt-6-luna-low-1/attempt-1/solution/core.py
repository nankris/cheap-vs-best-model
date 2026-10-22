"""SemVer precedence sorting."""

from functools import cmp_to_key


def _parse(version):
    # Inputs are guaranteed to be valid SemVer strings. Split build metadata
    # away first because it has no effect on precedence.
    core_and_pre, _, _build = version.partition("+")
    core, separator, prerelease = core_and_pre.partition("-")
    major, minor, patch = (int(part) for part in core.split("."))
    identifiers = prerelease.split(".") if separator else None
    return major, minor, patch, identifiers


def _compare_identifiers(left, right):
    for a, b in zip(left, right):
        a_numeric = a.isdigit()
        b_numeric = b.isdigit()
        if a_numeric and b_numeric:
            ai, bi = int(a), int(b)
            if ai != bi:
                return -1 if ai < bi else 1
        elif a_numeric != b_numeric:
            return -1 if a_numeric else 1
        elif a != b:
            # SemVer nonnumeric identifiers are ASCII; ordinary lexical
            # string ordering therefore matches the required comparison.
            return -1 if a < b else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1


def _compare_versions(left, right):
    lmajor, lminor, lpatch, lpre = _parse(left)
    rmajor, rminor, rpatch, rpre = _parse(right)
    for a, b in ((lmajor, rmajor), (lminor, rminor), (lpatch, rpatch)):
        if a != b:
            return -1 if a < b else 1
    if lpre is None or rpre is None:
        if lpre is rpre:
            return 0
        return 1 if lpre is None else -1
    return _compare_identifiers(lpre, rpre)


def solve(rows):
    """Return a stable ascending precedence ordering of version strings."""
    return sorted(rows, key=cmp_to_key(_compare_versions))
