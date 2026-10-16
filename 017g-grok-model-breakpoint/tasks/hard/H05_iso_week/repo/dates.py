import datetime as dt

def parse_iso(text):
    try:
        year, month, day = (int(part) for part in text.split("-"))
        return dt.date(year, month, day)
    except Exception as exc:
        raise ValueError(text) from exc
