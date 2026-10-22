import json


def decode(payload):
    """Decode a JSON array of integer interval pairs."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("payload must be a JSON array")

    intervals = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ValueError("each interval must contain exactly two endpoints")
        start, end = row
        if type(start) is not int or type(end) is not int:
            raise ValueError("interval endpoints must be integers")
        intervals.append((min(start, end), max(start, end)))
    return intervals
