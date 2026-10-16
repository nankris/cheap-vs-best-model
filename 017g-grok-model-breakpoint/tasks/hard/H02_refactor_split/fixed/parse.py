def parse_rows(records):
    parsed = []
    skipped = 0
    for rec in records:
        if not isinstance(rec, dict):
            skipped += 1
            continue
        id_ = str(rec.get("id", "")).strip()
        name = str(rec.get("name", "")).strip()
        raw_qty = str(rec.get("qty", "")).strip()
        if id_ == "" or name == "":
            skipped += 1
            continue
        try:
            qty = int(raw_qty)
        except ValueError:
            skipped += 1
            continue
        if qty < 0:
            skipped += 1
            continue
        parsed.append({"id": id_, "name": name, "qty": qty})
    return parsed, skipped
