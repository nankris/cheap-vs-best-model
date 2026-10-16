def is_v2(record):
    return isinstance(record, dict) and record.get("version") == 2
