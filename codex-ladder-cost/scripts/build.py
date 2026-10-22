import json,copy,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'codex-model-breakpoint'
JOURNAL='''
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
'''
BATCH='''API api.run(payload:str)->str. Payload is a JSON list of algorithm inputs. Return a JSON list of outputs, one per input in original order. Implement an immutable frozen model.Result(value) dataclass; service.compute(rows) must return Result(core.solve(rows)); render.present(result) must return json.dumps(result.value) string. All three are public and independently tested. api.run must apply this pipeline to each input; inputs are valid. Never mutate caller data. No persistent state across calls. Algorithm:\n'''
def fixture(t,p,reference=False):
 p.mkdir(parents=True,exist_ok=True)
 files={'TASK.md':t['spec'],'core.py':t['reference'] if reference else '# Legacy: only the first item matters.\ndef solve(rows):\n    return None\n'}
 if t['tier']==1:
  files['api.py']='import json\nfrom core import solve\ndef run(payload): return json.dumps(solve(json.loads(payload)))\n'
 else:
  files.update({'model.py':'from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Result:\n    value: object\n' if reference else '# Legacy: mutable dictionaries are the canonical result type.\nResult = dict\n','service.py':'from model import Result\nfrom core import solve\ndef compute(rows): return Result(solve(rows))\n' if reference else 'from core import solve\ndef compute(rows): return solve(rows)\n','render.py':'import json\nfrom model import Result\ndef present(result): return json.dumps(result.value)\n' if reference else '# Legacy: str() is JSON compatible.\ndef present(value): return str(value)\n'})
  if t['tier']==2:
   files['api.py']='import json\nfrom service import compute\nfrom render import present\ndef run(payload): return present(compute(json.loads(payload)))\n'
  elif t['tier']==3:
   files['api.py']='import json\nfrom service import compute\nfrom render import present\ndef run(payload): return json.dumps([json.loads(present(compute(x))) for x in json.loads(payload)])\n' if reference else 'from service import compute\nfrom render import present\ndef run(payload): return present(compute(payload))\n'
  else:
   files['api.py']=(ROOT/'scripts/journal_reference.py').read_text() if reference else '# Legacy: ids are state keys; snapshots need only shallow copies.\nimport json\nfrom service import compute\nfrom render import present\ndef run(payload):\n    return json.dumps([present(compute(x)) for x in json.loads(payload)])\n'
 for name,s in files.items(): (p/name).write_text(s)

def cases(t):
 base=copy.deepcopy(t['cases'])
 if t['tier']<=2:return base
 if t['tier']==3:return [[],base,base[::-1],base[:1]*3]
 rng=random.Random(1703+int(t['id'][1:])); out=[]
 for i,c in enumerate(base):
  # Every base boundary input is exercised through all lifecycle operations.
  out.append([{'op':'put','key':'','input':c,'id':'p'}, {'op':'begin','id':'b'}, {'op':'begin','id':'b'}, {'op':'delete','key':''}, {'op':'rollback','id':'r'}, {'op':'rollback','id':'r'}, {'op':'get','key':''}, {'op':'put','key':'','input':c,'id':'p'}, {'op':'put','key':'x','input':c,'id':'p'}, {'op':'list'}, {'op':'commit'}, {'op':'get','key':'x','id':'p'}, {'op':'list','id':None}, {'op':'get','key':1}, {'op':'expect','key':'','value':None}])
 # Random state traces independent of outputs; exercise nested ownership and cache errors.
 for z in range(12):
  ops=[]
  for j in range(50):
   op=rng.choice(['put','put','get','delete','begin','commit','rollback','expect','list','bad'])
   d={'op':op}
   if op in ['put','get','delete','expect']:d['key']=rng.choice(['a','b','','é'])
   if op=='put':d['input']=copy.deepcopy(rng.choice(base))
   if op=='expect':d['value']=rng.choice([None,False,[],{},0,''])
   if rng.random()<.35:d['id']=rng.choice(['','x','y','z',None,1])
   if rng.random()<.1:d['extra']=rng.choice([0,1])
   ops.append(d)
  out.append(ops)
 out.extend([[],[None,3,[],{}, {'op':'put','key':'a'},{'op':'get'},{'op':'expect','key':'a'}], [{'op':'get','key':'a','id':'x'},{'op':'list','id':'x'},{'op':'list','id':'x'}]])
 return out

def build():
 a=json.loads((OLD/'suite.json').read_text());b=json.loads((OLD/'suite2.json').read_text())
 tasks=[]
 for tier,items in [(1,a[10:14]),(2,a[:5]),(3,b[:5]),(4,a[:10]+b)]:
  for item in items:
   t=copy.deepcopy(item);t['tier']=tier;t['id']=f'T{len(tasks)+1:02}';t['algorithm_spec']=t['spec']
   if t['name']=='refactor':
    t['algorithm_spec']='Rows are decimal strings. Round EACH value to integer cents using exact Decimal and half-even rounding, then sum cents. Return the balance as a decimal STRING with exactly two places, including a minus sign only for negative totals. Empty input returns \"0.00\". Preserve input order independence. core.py additionally exports frozen dataclass Money(cents:int), classmethod Money.parse(decimal_string) rounding to cents, and __add__ returning Money. The journal Result pipeline above supersedes all old Money-specific service/render signatures.'
   t['spec']= ('API api.run(payload:str)->str, JSON input/output. Fix core.solve. Algorithm:\n' if tier==1 else 'API api.run(payload:str)->str, JSON input/output. Fix the chained modules. Algorithm:\n' if tier==2 else BATCH if tier==3 else JOURNAL)+t['algorithm_spec']
   tasks.append(t)
 (ROOT/'private/suite.json').write_text(json.dumps(tasks,indent=2))
 print('built',len(tasks),'tasks')
if __name__=='__main__':build()
