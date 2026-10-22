import json


def present(value):
    """Encode the result as JSON (including JSON null for unreachable paths)."""
    return json.dumps(value)
