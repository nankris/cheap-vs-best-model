import copy


_MISSING = object()


def _tokens(pointer):
    if not isinstance(pointer, str):
        raise ValueError("invalid pointer")
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError("invalid pointer")
    out = []
    for raw in pointer[1:].split("/"):
        token = ""
        i = 0
        while i < len(raw):
            if raw[i] != "~":
                token += raw[i]
                i += 1
            elif i + 1 < len(raw) and raw[i + 1] in "01":
                token += "/" if raw[i + 1] == "1" else "~"
                i += 2
            else:
                raise ValueError("invalid escape")
        out.append(token)
    return out


def _index(token, length, allow_end=False):
    if token == "-" and allow_end:
        return length
    if not token or (len(token) > 1 and token[0] == "0") or not token.isascii() or not token.isdigit():
        raise ValueError("invalid index")
    n = int(token)
    if n < 0 or n > length or (n == length and not allow_end):
        raise ValueError("index out of range")
    return n


def _get(root, tokens):
    current = root
    for token in tokens:
        if isinstance(current, dict):
            if token not in current:
                raise ValueError("missing target")
            current = current[token]
        elif isinstance(current, list):
            current = current[_index(token, len(current))]
        else:
            raise ValueError("not a container")
    return current


def _apply(root, operation):
    if not isinstance(operation, list) or len(operation) not in (2, 3):
        raise ValueError("invalid operation")
    op = operation[0]
    if op not in ("add", "replace", "remove", "test"):
        raise ValueError("invalid operation")
    if op == "remove":
        if len(operation) != 2:
            raise ValueError("invalid operation")
    elif len(operation) != 3:
        raise ValueError("invalid operation")
    tokens = _tokens(operation[1])
    if op == "test":
        actual = _get(root, tokens)
        if actual != operation[2]:
            raise ValueError("test failed")
        return root
    value = copy.deepcopy(operation[2]) if op != "remove" else None
    if not tokens:
        if op == "remove":
            return None
        return value
    parent = _get(root, tokens[:-1])
    token = tokens[-1]
    if isinstance(parent, dict):
        if op in ("replace", "remove") and token not in parent:
            raise ValueError("missing target")
        if op == "remove":
            del parent[token]
        else:
            parent[token] = value
    elif isinstance(parent, list):
        idx = _index(token, len(parent), allow_end=(op == "add"))
        if op == "add":
            parent.insert(idx, value)
        elif op == "replace":
            parent[idx] = value
        else:
            del parent[idx]
    else:
        raise ValueError("not a container")
    return root


def solve(rows):
    original = copy.deepcopy(rows[0])
    document = copy.deepcopy(original)
    try:
        operations = rows[1]
        if not isinstance(operations, list):
            raise ValueError("operations must be a list")
        for operation in operations:
            document = _apply(document, operation)
    except (ValueError, IndexError, KeyError, TypeError, AttributeError):
        return {"ok": False, "document": original}
    return {"ok": True, "document": document}
