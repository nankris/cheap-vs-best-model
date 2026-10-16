from copy import deepcopy


class _InvalidOperation(Exception):
    pass


def _pointer(path):
    if not isinstance(path, str):
        raise _InvalidOperation
    if path == "":
        return []
    if not path.startswith("/"):
        raise _InvalidOperation
    tokens = []
    for token in path[1:].split("/"):
        decoded = []
        index = 0
        while index < len(token):
            char = token[index]
            if char == "~":
                index += 1
                if index == len(token) or token[index] not in "01":
                    raise _InvalidOperation
                char = "~" if token[index] == "0" else "/"
            decoded.append(char)
            index += 1
        tokens.append("".join(decoded))
    return tokens


def _index(token, size, inserting=False):
    if inserting and token == "-":
        return size
    if not token or any(char not in "0123456789" for char in token):
        raise _InvalidOperation
    if len(token) > 1 and token[0] == "0":
        raise _InvalidOperation
    # Bound before converting, including indices too long for Python's int().
    if len(token) > len(str(size)):
        raise _InvalidOperation
    index = int(token)
    if index > size or (index == size and not inserting):
        raise _InvalidOperation
    return index


def _lookup(container, token):
    if isinstance(container, dict):
        if token not in container:
            raise _InvalidOperation
        return container[token]
    if isinstance(container, list):
        return container[_index(token, len(container))]
    raise _InvalidOperation


def _equal(left, right):
    # Python treats True as 1; JSON treats booleans and numbers separately.
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _apply(document, operation):
    if not isinstance(operation, list) or not operation:
        raise _InvalidOperation
    op = operation[0]
    if op not in ("add", "replace", "remove", "test"):
        raise _InvalidOperation
    if len(operation) != (2 if op == "remove" else 3):
        raise _InvalidOperation
    tokens = _pointer(operation[1])
    if not tokens:
        if op == "test":
            if not _equal(document, operation[2]):
                raise _InvalidOperation
            return document
        return None if op == "remove" else deepcopy(operation[2])

    parent = document
    for token in tokens[:-1]:
        parent = _lookup(parent, token)
    token = tokens[-1]
    if op == "test":
        if not _equal(_lookup(parent, token), operation[2]):
            raise _InvalidOperation
    elif isinstance(parent, dict):
        if op != "add" and token not in parent:
            raise _InvalidOperation
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
        raise _InvalidOperation
    return document


def solve(rows):
    original, operations = rows
    document = deepcopy(original)
    try:
        for operation in operations:
            document = _apply(document, operation)
    except _InvalidOperation:
        return {"ok": False, "document": deepcopy(original)}
    return {"ok": True, "document": document}
