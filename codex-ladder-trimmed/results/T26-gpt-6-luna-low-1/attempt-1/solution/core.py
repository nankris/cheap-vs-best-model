import re


_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _precedence(row):
    match = _SEMVER.fullmatch(row)
    # Inputs are guaranteed valid SemVer, so this is defensive only.
    if match is None:
        raise ValueError("invalid SemVer")
    major, minor, patch, prerelease = match.groups()
    version = (int(major), int(minor), int(patch))
    if prerelease is None:
        return version, 1, ()
    identifiers = []
    for identifier in prerelease.split("."):
        if identifier.isdigit():
            identifiers.append((0, int(identifier)))
        else:
            identifiers.append((1, identifier))
    return version, 0, tuple(identifiers)


def solve(rows):
    """Return rows in stable ascending SemVer precedence order."""
    return sorted(rows, key=_precedence)
