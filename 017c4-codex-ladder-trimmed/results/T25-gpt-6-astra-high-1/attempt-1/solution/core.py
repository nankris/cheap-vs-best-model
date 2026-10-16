"""Apply an atomic sequence of JSON Patch operations."""

from copy import deepcopy


class _InvalidPatch(Exception):
    pass


def _pointer(path):
    if not isinstance(path, str):
        raise _InvalidPatch
    if path == "":
        return []
    if not path.startswith("/"):
        raise _InvalidPatch
    tokens = []
    for token in path[1:].split("/"):
        decoded = []
        index = 0
        while index < len(token):
            char = token[index]
            if char == "~":
                index += 1
                if index == len(token) or token[index] not in "01":
                    raise _InvalidPatch
                char = "~" if token[index] == "0" else "/"
            decoded.append(char)
            index += 1
        tokens.append("".join(decoded))
    return tokens


def _index(token, length, insert=False):
    if insert and token == "-":
        return length
    if not token or any(char not in "0123456789" for char in token):
        raise _InvalidPatch
    if len(token) > 1 and token[0] == "0":
        raise _InvalidPatch
    # Compare before converting, including for arbitrarily long invalid indices.
    limit = length if insert else length - 1
    bound = str(limit)
    if limit < 0 or len(token) > len(bound):
        raise _InvalidPatch
    if len(token) == len(bound) and token > bound:
        raise _InvalidPatch
    return int(token)


def _get(document, token):
    if isinstance(document, dict):
        if token not in document:
            raise _InvalidPatch
        return document[token]
    if isinstance(document, list):
        return document[_index(token, len(document))]
    raise _InvalidPatch


def _apply(document, operation):
    if not isinstance(operation, list) or not operation:
        raise _InvalidPatch
    op = operation[0]
    if op not in ("add", "replace", "remove", "test"):
        raise _InvalidPatch
    if len(operation) != (2 if op == "remove" else 3):
        raise _InvalidPatch
    tokens = _pointer(operation[1])
    if not tokens:
        if op == "test":
            if document != operation[2]:
                raise _InvalidPatch
            return document
        return None if op == "remove" else deepcopy(operation[2])

    parent = document
    for token in tokens[:-1]:
        parent = _get(parent, token)
    token = tokens[-1]
    if op == "test":
        if _get(parent, token) != operation[2]:
            raise _InvalidPatch
    elif isinstance(parent, dict):
        if op != "add" and token not in parent:
            raise _InvalidPatch
        if op == "remove":
            del parent[token]
        else:
            parent[token] = deepcopy(operation[2])
    elif isinstance(parent, list):
        index = _index(token, len(parent), insert=op == "add")
        if op == "add":
            parent.insert(index, deepcopy(operation[2]))
        elif op == "remove":
            del parent[index]
        else:
            parent[index] = deepcopy(operation[2])
    else:
        raise _InvalidPatch
    return document


def solve(rows):
    original, operations = rows
    document = deepcopy(original)
    try:
        for operation in operations:
            document = _apply(document, operation)
    except _InvalidPatch:
        return {"ok": False, "document": deepcopy(original)}
    return {"ok": True, "document": document}
