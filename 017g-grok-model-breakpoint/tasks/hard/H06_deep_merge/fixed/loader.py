from defaults import DEFAULTS
from merge import deep_merge

ALLOWED = {"service", "debug", "db", "limits", "tags"}

def load(override):
    if not isinstance(override, dict):
        raise ValueError("override")
    for key in override:
        if key not in ALLOWED:
            raise ValueError(key)
    merged = deep_merge(DEFAULTS, override)
    if "service" in merged and not isinstance(merged["service"], str):
        raise ValueError("service")
    limits = merged.get("limits")
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits")
        if "max_conn" in limits and (
            not isinstance(limits["max_conn"], int) or isinstance(limits["max_conn"], bool)
        ):
            raise ValueError("max_conn")
    return merged
