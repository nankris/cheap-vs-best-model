
PUBLIC API: api.run(payload: str) -> str (JSON in, JSON out). Replace the legacy chain with the following journal. Algorithm inputs below are valid; journal control inputs may be invalid as specified. No third-party packages.

Input is a list of command dictionaries. Output is {"events": [...], "state": [[key,value], ...], "depth": integer}. State is sorted by key (Unicode order). Each command yields exactly one event. Never mutate caller data. State starts empty, stack starts empty, idempotency cache starts empty for EACH run. Do not retain anything across run calls.

Commands:
- {"op":"put","key":string,"input":algorithm_input}: compute algorithm value, store under key, return {"ok":value}. Empty keys are valid.
- {"op":"get","key":string}: return {"ok":stored_value}; absent key returns {"error":"missing"}.
- {"op":"delete","key":string}: delete existing key and return {"ok":old_value}; absent returns missing error.
- {"op":"begin"}: push DEEP snapshot of state; return {"ok":new_depth}.
- {"op":"commit"}: discard latest savepoint, retaining current state. Return {"ok":new_depth}. With no savepoint return {"error":"transaction"}.
- {"op":"rollback"}: restore latest snapshot and pop it. Return {"ok":new_depth}. With no savepoint return transaction error.
- {"op":"expect","key":string,"value":JSON}: return {"ok":true} if existing state value equals value by Python JSON equality (bool equals 0/1); otherwise {"error":"expectation"}. This does not rollback anything.
- {"op":"list"}: return {"ok":[[key,value],...]} sorted by key.
- Unknown op, missing required fields, non-string key, non-string supplied id: return {"error":"command"}. Ignore extra fields for command execution but INCLUDE THEM in idempotency identity. Explicit null id is invalid. A command is a dictionary; non-dicts are command errors. Validation of required fields happens before execution. All malformed control commands are atomic and leave state, stack and cache unchanged.

OPTIONAL idempotency: any command may have a string "id" (empty string valid). Cache ONLY successful events (events containing "ok"). Identity is the full command after removing id, compared by Python equality of JSON structures (object key order irrelevant). Before ordinary command validation/execution, check the id if it is a valid string and already cached: identical identity REPLAYS a deep copy of the original event WITHOUT side effects (even begin/rollback/list); changed identity returns {"error":"id-conflict"}. Cache lives OUTSIDE savepoints: rollback never rewinds cache. Failed operations do not reserve ids. Never alias cached or returned mutable values to live state. Deep copies at every ownership boundary. Id cache resets for each API invocation. Commands without ids execute normally every time. Cache lookup precedes required-field validation, but invalid/non-string supplied id always yields command error.

REFACTOR CONTRACT (hidden tests import these modules directly): model.py exports frozen dataclass Result with ONE field value (arbitrary JSON), core.py exports solve(rows) implementing only the algorithm below; service.py exports compute(rows) returning Result(core.solve(rows)); render.py exports present(result: Result) returning the value JSON-serialized to a STRING; api.py exports run and uses this pipeline for puts. model.Result must be the same class imported by service and render; direct compute outputs must be Result, not dictionaries. Preserve scalar/list/null algorithm outputs exactly. A frozen dataclass prevents rebinding its field; deep-copy ownership is a separate journal responsibility. Tests call compute and present independently, not only api.run. Legacy comments may contradict this contract; this spec takes precedence.

Order of validation details: op must be recognized before executing. put requires key and input, get/delete require key, expect requires key and value. begin/commit/rollback/list need no other fields. For required key fields, key must be str. JSON serialization accepts Unicode and ordinary standard-library number semantics. Journal input itself is a list. Algorithm exceptions are outside scope because all algorithm inputs are valid. No new semantics should be inferred from old placeholder files.

ALGORITHM FOR put AND core.solve:
Rows are [key,integer_version,value_or_null]. For each key choose greatest version, last row on ties. Null is a deletion and removes that key. Return sorted [key,value] rows. Do not confuse false, 0, or empty string with deletion.