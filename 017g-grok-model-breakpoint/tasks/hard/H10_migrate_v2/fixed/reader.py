from migrate import to_v2

def load(record):
    if not isinstance(record, dict):
        raise ValueError("record")
    migrated = to_v2(record)
    name = migrated.get("name")
    if not isinstance(name, str) or name.strip() == "":
        raise ValueError("name")
    return migrated
