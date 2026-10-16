from cache import Cache
from compute import build

_cache = Cache()
_calls = {"n": 0}

def clear():
    _cache.clear()
    _calls["n"] = 0

def call_count():
    return _calls["n"]

def bust(user):
    _cache.drop_user(user)

def get_view(user, include_archived=False, role="viewer"):
    key = (user, bool(include_archived), role)
    hit = _cache.get(key)
    if hit is not None:
        return list(hit)
    _calls["n"] += 1
    rows = build(user, include_archived=include_archived, role=role)
    _cache.put(key, list(rows))
    return list(rows)
