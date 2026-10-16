def solve(rows):
    """Match a glob against the entire text, using Unicode codepoints."""
    pattern, text = rows
    # matched[j] records whether the processed pattern matches text[:j].
    matched = [True] + [False] * len(text)
    index = 0
    while index < len(pattern):
        token = pattern[index]
        index += 1
        kind = "literal"
        if token == "\\":
            if index < len(pattern):
                token = pattern[index]
                index += 1
        elif token == "?":
            kind = "one"
        elif token == "*":
            kind = "star"
            if index < len(pattern) and pattern[index] == "*":
                kind = "globstar"
                index += 1

        current = [False] * (len(text) + 1)
        if kind in ("star", "globstar"):
            current[0] = matched[0]
            for end, char in enumerate(text, 1):
                current[end] = matched[end] or (
                    current[end - 1] and (kind == "globstar" or char != "/")
                )
        else:
            for end, char in enumerate(text, 1):
                accepts = char != "/" if kind == "one" else char == token
                current[end] = matched[end - 1] and accepts
        matched = current

    return matched[-1]
