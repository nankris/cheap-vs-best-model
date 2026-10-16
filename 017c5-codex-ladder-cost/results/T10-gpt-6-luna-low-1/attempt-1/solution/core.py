from copy import deepcopy


class _InvalidOperation(Exception):
    pass


def _pointer_parts(path):
    if not isinstance(path, str):
        raise _InvalidOperation
    if path == "":
        return []
    if not path.startswith("/"):
        raise _InvalidOperation

    parts = []
    for encoded in path[1:].split("/"):
        decoded = ""
        i = 0
        while i < len(encoded):
            char = encoded[i]
            if char == "~":
                if i + 1 >= len(encoded) or encoded[i + 1] not in "01":
                    raise _InvalidOperation
                decoded += "/" if encoded[i + 1] == "1" else "~"
                i += 2
            else:
                decoded += char
                i += 1
        parts.append(decoded)
    return parts


def _list_index(token, length, allow_end=False):
    if token == "-":
        if allow_end:
            return length
        raise _InvalidOperation
    if not token or (len(token) > 1 and token[0] == "0"):
        raise _InvalidOperation
    if not token.isascii() or not token.isdigit():
        raise _InvalidOperation
    index = int(token)
    if index < 0 or index > length if allow_end else index >= length:
        raise _InvalidOperation
    return index


def _get_parent(document, parts):
    current = document
    for token in parts[:-1]:
        if isinstance(current, dict):
            if token not in current:
                raise _InvalidOperation
            current = current[token]
        elif isinstance(current, list):
            current = current[_list_index(token, len(current))]
        else:
            raise _InvalidOperation
    return current


def _get(document, parts):
    if not parts:
        return document
    parent = _get_parent(document, parts)
    token = parts[-1]
    if isinstance(parent, dict):
        if token not in parent:
            raise _InvalidOperation
        return parent[token]
    if isinstance(parent, list):
        return parent[_list_index(token, len(parent))]
    raise _InvalidOperation


def _apply(document, operation):
    if not isinstance(operation, list) or len(operation) not in (2, 3):
        raise _InvalidOperation
    op = operation[0]
    path = operation[1]
    if op not in ("add", "replace", "remove", "test"):
        raise _InvalidOperation
    if (op == "remove" and len(operation) != 2) or (op != "remove" and len(operation) != 3):
        raise _InvalidOperation
    parts = _pointer_parts(path)

    if op == "test":
        if _get(document, parts) != operation[2]:
            raise _InvalidOperation
        return document

    if not parts:
        if op == "remove":
            return None
        if op in ("add", "replace"):
            return deepcopy(operation[2])

    parent = _get_parent(document, parts)
    token = parts[-1]
    if isinstance(parent, dict):
        if op in ("replace", "remove") and token not in parent:
            raise _InvalidOperation
        if op == "remove":
            del parent[token]
        else:
            parent[token] = deepcopy(operation[2])
        return document
    if isinstance(parent, list):
        if op == "add":
            index = _list_index(token, len(parent), allow_end=True)
            parent.insert(index, deepcopy(operation[2]))
        elif op == "replace":
            index = _list_index(token, len(parent))
            parent[index] = deepcopy(operation[2])
        else:
            index = _list_index(token, len(parent))
            del parent[index]
        return document
    raise _InvalidOperation


def solve(rows):
    """Apply a sequence of JSON Pointer operations atomically to one document."""
    try:
        if not isinstance(rows, list) or len(rows) != 2:
            raise _InvalidOperation
        original, operations = rows
        if not isinstance(operations, list):
            raise _InvalidOperation
        document = deepcopy(original)
        for operation in operations:
            document = _apply(document, operation)
        return {"ok": True, "document": document}
    except _InvalidOperation:
        return {"ok": False, "document": deepcopy(rows[0]) if isinstance(rows, list) and rows else None}
