from schema import is_v2

def to_v2(record):
    if not isinstance(record, dict):
        raise ValueError("record")
    if is_v2(record):
        return dict(record)
    out = {}
    for key, value in record.items():
        if key in ("full_name", "age", "version"):
            continue
        out[key] = value
    name = str(record.get("full_name", "")).strip()
    if name == "":
        raise ValueError("name")
    out["name"] = name
    if "age" in record:
        age_text = str(record["age"]).strip()
        if not age_text.isdigit():
            raise ValueError("age")
        out["age"] = int(age_text)
    out["version"] = 2
    return out
