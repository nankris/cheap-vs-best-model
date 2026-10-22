import json
def decode(payload):
    """Decode a JSON payload containing interval rows."""
    value = json.loads(payload)
    # Accept either the interval list itself or the conventional named field.
    if isinstance(value, dict):
        if "rows" in value:
            value = value["rows"]
        elif "intervals" in value:
            value = value["intervals"]
        else:
            raise ValueError("payload object must contain 'rows' or 'intervals'")
    if not isinstance(value, list):
        raise ValueError("payload must be a JSON array of intervals")
    rows = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ValueError("each interval must contain exactly two endpoints")
        start, end = row
        if isinstance(start, bool) or not isinstance(start, int) or isinstance(end, bool) or not isinstance(end, int):
            raise ValueError("interval endpoints must be integers")
        rows.append((start, end))
    return rows
