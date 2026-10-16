def _tokens(pattern):
    """Tokenize a glob pattern, keeping escaped metacharacters literal."""
    tokens = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\":
            if i + 1 < len(pattern):
                tokens.append(("literal", pattern[i + 1]))
                i += 2
            else:
                tokens.append(("literal", "\\"))
                i += 1
        elif char == "?":
            tokens.append(("one", None))
            i += 1
        elif char == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                tokens.append(("many", None))
                i += 2
            else:
                tokens.append(("segment", None))
                i += 1
        else:
            tokens.append(("literal", char))
            i += 1
    return tokens


def _matches(pattern, text):
    tokens = _tokens(pattern)

    # Dynamic programming over codepoints avoids regex escaping pitfalls and
    # handles adjacent wildcard operators with the same explicit semantics.
    previous = [False] * (len(text) + 1)
    previous[0] = True
    for kind, value in tokens:
        current = [False] * (len(text) + 1)
        if kind == "literal":
            for j, char in enumerate(text, 1):
                current[j] = previous[j - 1] and char == value
        elif kind == "one":
            for j, char in enumerate(text, 1):
                current[j] = previous[j - 1] and char != "/"
        elif kind == "segment":
            current[0] = previous[0]
            for j, char in enumerate(text, 1):
                current[j] = previous[j] or (char != "/" and current[j - 1])
        else:  # ** consumes any number of codepoints, including slash.
            current[0] = previous[0]
            for j in range(1, len(text) + 1):
                current[j] = previous[j] or current[j - 1]
        previous = current
    return previous[len(text)]


def solve(rows):
    """Return full-match results for a sequence of [pattern, text] pairs."""
    return [_matches(pattern, text) for pattern, text in rows]
