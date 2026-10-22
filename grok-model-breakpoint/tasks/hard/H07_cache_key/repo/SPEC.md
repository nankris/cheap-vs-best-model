# View cache

`compute.build(user, include_archived=False, role="viewer")` is the expensive function. It appends:

- `"<user>:active"` always
- `"<user>:archived"` when `include_archived` is true
- `"<user>:secret"` when `role` is `"admin"`

`views.get_view(user, include_archived=False, role="viewer")` returns that list, cached. The cache key is the user, the archived flag, and the role. Different combinations must not share an entry.

- A repeat call with the same arguments must not call `compute.build` again.
- `views.call_count()` is the number of `compute.build` calls since `views.clear()`.
- `views.bust(user)` drops every cached entry for that user and no other user.
- `views.clear()` drops the whole cache and resets the counter.

The visible test calls `ada` twice with different `include_archived` values and expects two computes. It never asks for `role="admin"` and never calls `bust`.
