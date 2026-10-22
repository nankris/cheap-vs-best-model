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
        i = 0
        while i < len(token):
            if token[i] == "~":
                if i + 1 == len(token) or token[i + 1] not in "01":
                    raise _InvalidPatch
                decoded.append("~" if token[i + 1] == "0" else "/")
                i += 2
            else:
                decoded.append(token[i])
                i += 1
        tokens.append("".join(decoded))
    return tokens


def _index(token, length, inserting=False):
    if inserting and token == "-":
        return length
    if not token or any(char not in "0123456789" for char in token):
        raise _InvalidPatch
    if len(token) > 1 and token[0] == "0":
        raise _InvalidPatch
    # Bound before conversion, including indices exceeding Python's int limit.
    maximum = length if inserting else length - 1
    if maximum < 0 or len(token) > len(str(maximum)):
        raise _InvalidPatch
    index = int(token)
    if index > maximum:
        raise _InvalidPatch
    return index


def _get(container, token):
    if isinstance(container, dict):
        if token not in container:
            raise _InvalidPatch
        return container[token]
    if isinstance(container, list):
        return container[_index(token, len(container))]
    raise _InvalidPatch


def _equal(left, right):
    # JSON booleans and numbers are distinct, unlike Python's True and 1.
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _equal(a, b) for a, b in zip(left, right)
        )
    return left == right


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
            if not _equal(document, operation[2]):
                raise _InvalidPatch
            return document
        return None if op == "remove" else deepcopy(operation[2])

    parent = document
    for token in tokens[:-1]:
        parent = _get(parent, token)
    token = tokens[-1]

    if op == "test":
        if not _equal(_get(parent, token), operation[2]):
            raise _InvalidPatch
    elif isinstance(parent, dict):
        if op != "add" and token not in parent:
            raise _InvalidPatch
        if op == "remove":
            del parent[token]
        else:
            parent[token] = deepcopy(operation[2])
    elif isinstance(parent, list):
        index = _index(token, len(parent), inserting=op == "add")
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
