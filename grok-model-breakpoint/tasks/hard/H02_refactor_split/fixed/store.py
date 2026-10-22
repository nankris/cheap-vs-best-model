def upsert(parsed_rows):
    out = {}
    for row in parsed_rows:
        out[row["id"]] = {"name": row["name"], "qty": row["qty"]}
    return out
