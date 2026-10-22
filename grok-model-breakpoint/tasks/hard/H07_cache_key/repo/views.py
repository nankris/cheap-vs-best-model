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
    key = user
    hit = _cache.get(key)
    if hit is not None:
        return hit
    _calls["n"] += 1
    rows = build(user, include_archived=include_archived, role=role)
    _cache.put(key, rows)
    return rows
