"""Implementation of the document operation contract."""

from copy import deepcopy


class _InvalidOperation(Exception):
    pass


def _tokens(pointer):
    if not isinstance(pointer, str):
        raise _InvalidOperation
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise _InvalidOperation
    result = []
    for token in pointer[1:].split("/"):
        decoded = []
        i = 0
        while i < len(token):
            ch = token[i]
            if ch != "~":
                decoded.append(ch)
                i += 1
                continue
            if i + 1 >= len(token) or token[i + 1] not in "01":
                raise _InvalidOperation
            decoded.append("/" if token[i + 1] == "1" else "~")
            i += 2
        result.append("".join(decoded))
    return result


def _list_index(token, size, allow_end=False):
    if token == "-":
        if allow_end:
            return size
        raise _InvalidOperation
    if not token or (len(token) > 1 and token[0] == "0"):
        raise _InvalidOperation
    if any(ch < "0" or ch > "9" for ch in token):
        raise _InvalidOperation
    index = int(token)
    if index > size if allow_end else index >= size:
        raise _InvalidOperation
    return index


def _get(container, token):
    if isinstance(container, dict):
        if token not in container:
            raise _InvalidOperation
        return container[token]
    if isinstance(container, list):
        return container[_list_index(token, len(container))]
    raise _InvalidOperation


def _apply(document, operation):
    if not isinstance(operation, list) or len(operation) not in (2, 3):
        raise _InvalidOperation
    op, pointer = operation[0], operation[1]
    if op not in ("add", "replace", "remove", "test"):
        raise _InvalidOperation
    expected_len = 2 if op == "remove" else 3
    if len(operation) != expected_len:
        raise _InvalidOperation
    path = _tokens(pointer)

    if op == "test":
        target = document
        for token in path:
            target = _get(target, token)
        if target != operation[2]:
            raise _InvalidOperation
        return document

    if not path:
        if op == "remove":
            return None
        if op == "replace":
            return deepcopy(operation[2])
        return deepcopy(operation[2])

    parent = document
    for token in path[:-1]:
        parent = _get(parent, token)
    token = path[-1]

    if isinstance(parent, dict):
        if op in ("replace", "remove") and token not in parent:
            raise _InvalidOperation
        if op == "remove":
            del parent[token]
        else:
            parent[token] = deepcopy(operation[2])
    elif isinstance(parent, list):
        if op == "add":
            index = _list_index(token, len(parent), allow_end=True)
            parent.insert(index, deepcopy(operation[2]))
        else:
            index = _list_index(token, len(parent))
            if op == "remove":
                del parent[index]
            else:
                parent[index] = deepcopy(operation[2])
    else:
        raise _InvalidOperation
    return document


def solve(rows):
    """Apply [operation, pointer, value] operations atomically to each input."""
    results = []
    for row in rows:
        original = deepcopy(row[0])
        working = deepcopy(original)
        try:
            if not isinstance(row, list) or len(row) != 2 or not isinstance(row[1], list):
                raise _InvalidOperation
            for operation in row[1]:
                working = _apply(working, operation)
        except ( _InvalidOperation, TypeError, ValueError, IndexError):
            results.append({"ok": False, "document": original})
        else:
            results.append({"ok": True, "document": working})
    return results
