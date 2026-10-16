def parse_and_store(records):
    out = {}
    for rec in records:
        id_ = rec["id"]
        if id_ in out:
            continue
        qty = int(rec["qty"])
        if qty < 0:
            raise ValueError("negative")
        out[id_] = {"name": rec["name"], "qty": qty}
    return {"rows": out, "skipped": 0}
