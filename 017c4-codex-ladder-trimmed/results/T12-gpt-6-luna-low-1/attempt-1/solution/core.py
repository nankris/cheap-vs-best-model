"""Glob matching implementation."""


def _tokens(pattern):
    """Tokenize a glob pattern, honoring escapes and treating ** as recursive."""
    tokens = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\":
            if i + 1 < len(pattern):
                i += 1
                tokens.append(("literal", pattern[i]))
            else:
                tokens.append(("literal", "\\"))
        elif char == "?":
            tokens.append(("single", None))
        elif char == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                tokens.append(("globstar", None))
                i += 1
            else:
                tokens.append(("star", None))
        else:
            tokens.append(("literal", char))
        i += 1
    return tokens


def solve(rows):
    """Return one full-match boolean for each [pattern, text] input row."""
    results = []
    for pattern, text in rows:
        tokens = _tokens(pattern)
        # Dynamic programming over pattern tokens and Unicode codepoints. Each
        # entry indicates whether the corresponding prefixes match.
        previous = [False] * (len(text) + 1)
        previous[0] = True
        for kind, value in tokens:
            current = [False] * (len(text) + 1)
            if kind in ("star", "globstar"):
                current[0] = previous[0]
                for j, char in enumerate(text, 1):
                    allowed = kind == "globstar" or char != "/"
                    current[j] = previous[j] or (allowed and current[j - 1])
            elif kind == "single":
                for j, char in enumerate(text, 1):
                    current[j] = char != "/" and previous[j - 1]
            else:
                for j, char in enumerate(text, 1):
                    current[j] = char == value and previous[j - 1]
            previous = current
        results.append(previous[len(text)])
    return results
