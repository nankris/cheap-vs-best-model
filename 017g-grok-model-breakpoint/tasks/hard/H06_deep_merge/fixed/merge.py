def _copy(value):
    if isinstance(value, dict):
        return {key: _copy(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return list(value)
    return value

def deep_merge(base, override):
    if not isinstance(override, dict):
        raise ValueError("override")
    out = _copy(base) if isinstance(base, dict) else {}
    for key, value in override.items():
        if value is None:
            out.pop(key, None)
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = _copy(value)
    return out
