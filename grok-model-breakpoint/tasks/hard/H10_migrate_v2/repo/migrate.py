def to_v2(record):
    out = dict(record)
    out["version"] = 2
    return out
