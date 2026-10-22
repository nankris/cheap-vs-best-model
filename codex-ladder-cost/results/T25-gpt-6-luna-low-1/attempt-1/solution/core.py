import copy


def _pointer_parts(path):
    if not isinstance(path, str):
        raise ValueError("invalid pointer")
    if path == "":
        return []
    if not path.startswith("/"):
        raise ValueError("invalid pointer")
    parts = []
    for raw in path[1:].split("/"):
        decoded = []
        i = 0
        while i < len(raw):
            if raw[i] == "~":
                if i + 1 >= len(raw) or raw[i + 1] not in "01":
                    raise ValueError("invalid escape")
                decoded.append("/" if raw[i + 1] == "1" else "~")
                i += 2
            else:
                decoded.append(raw[i])
                i += 1
        parts.append("".join(decoded))
    return parts


def _list_index(token, length, allow_end=False):
    if token == "-":
        if allow_end:
            return length
        raise ValueError("invalid index")
    if not token or (len(token) > 1 and token[0] == "0") or not token.isascii() or not token.isdigit():
        raise ValueError("invalid index")
    index = int(token)
    limit = length if allow_end else length - 1
    if index < 0 or index > limit:
        raise ValueError("index out of range")
    return index


def _parent(document, parts):
    node = document
    for token in parts[:-1]:
        if isinstance(node, dict):
            if token not in node:
                raise ValueError("missing member")
            node = node[token]
        elif isinstance(node, list):
            node = node[_list_index(token, len(node))]
        else:
            raise ValueError("not a container")
    return node


def _get(document, parts):
    if not parts:
        return document
    parent = _parent(document, parts)
    token = parts[-1]
    if isinstance(parent, dict):
        if token not in parent:
            raise ValueError("missing member")
        return parent[token]
    if isinstance(parent, list):
        return parent[_list_index(token, len(parent))]
    raise ValueError("not a container")


def _change(document, op, parts, value=None):
    if not parts:
        if op == "remove":
            return None
        return copy.deepcopy(value)
    parent = _parent(document, parts)
    token = parts[-1]
    if isinstance(parent, dict):
        if op in ("replace", "remove") and token not in parent:
            raise ValueError("missing member")
        if op == "remove":
            del parent[token]
        else:
            parent[token] = copy.deepcopy(value)
    elif isinstance(parent, list):
        if op == "add":
            parent.insert(_list_index(token, len(parent), allow_end=True), copy.deepcopy(value))
        else:
            index = _list_index(token, len(parent))
            if op == "remove":
                del parent[index]
            else:
                parent[index] = copy.deepcopy(value)
    else:
        raise ValueError("not a container")
    return document


def solve(rows):
    original = copy.deepcopy(rows[0])
    document = copy.deepcopy(rows[0])
    operations = rows[1]
    try:
        for operation in operations:
            if not isinstance(operation, list):
                raise ValueError("invalid operation")
            if len(operation) == 3 and operation[0] in ("add", "replace", "test"):
                op, path, value = operation
            elif len(operation) == 2 and operation[0] == "remove":
                op, path = operation
                value = None
            else:
                raise ValueError("invalid operation")
            parts = _pointer_parts(path)
            if op == "test":
                if _get(document, parts) != value:
                    raise ValueError("test failed")
            else:
                document = _change(document, op, parts, value)
    except (ValueError, IndexError, KeyError, TypeError):
        return {"ok": False, "document": original}
    return {"ok": True, "document": document}
