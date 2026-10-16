def deep_merge(base, override):
    out = dict(base)
    out.update(override)
    return out
