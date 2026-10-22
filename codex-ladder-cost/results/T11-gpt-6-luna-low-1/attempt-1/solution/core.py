import re


_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _precedence_parts(version):
    match = _SEMVER.fullmatch(version)
    # Inputs are specified to be valid SemVer strings. This guard makes a
    # violated precondition fail clearly rather than sorting incorrectly.
    if match is None:
        raise ValueError(f"invalid SemVer version: {version!r}")
    major, minor, patch, prerelease = match.groups()
    core = (int(major), int(minor), int(patch))
    if prerelease is None:
        # The release tuple sorts after every prerelease tuple for this core.
        return core, (1, ())
    identifiers = []
    for identifier in prerelease.split("."):
        if identifier.isdigit():
            identifiers.append((0, int(identifier)))
        else:
            identifiers.append((1, identifier))
    return core, (0, tuple(identifiers))


def solve(rows):
    # Python's sort is stable, so build metadata and equal precedence retain
    # the caller's original order and spelling.
    return sorted(rows, key=_precedence_parts)
