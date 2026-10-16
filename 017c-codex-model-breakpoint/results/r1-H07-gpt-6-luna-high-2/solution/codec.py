import json


def decode(payload):
    """Decode a JSON array of undirected string edges."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("payload must be a JSON array of edges")

    for edge in rows:
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or not all(isinstance(node, str) for node in edge)
        ):
            raise ValueError("each edge must be a pair of strings")
    return rows
