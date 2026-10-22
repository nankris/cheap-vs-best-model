from parse import parse_rows
from store import upsert

def run(records):
    parsed, skipped = parse_rows(records)
    return {"rows": upsert(parsed), "skipped": skipped}
