# Build order

`schedule.plan(nodes, edges)` returns a list. `edges` are `(before, after)` pairs: `before` must appear earlier than `after`. `schedule.CycleError` is the error type.

- Every name in `nodes` appears exactly once. A name with no edges is included.
- Duplicate edges count once.
- An edge that names something outside `nodes` raises `ValueError`.
- A cycle, including a self-loop, raises `CycleError`. Do not return a partial list.
- When several nodes are ready, pick the lexicographically smallest name.

The visible test is a two-node cycle. It does not check isolated nodes, ties, duplicate edges, or a self-loop.
