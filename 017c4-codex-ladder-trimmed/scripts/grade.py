import json,subprocess,sys,tempfile
from pathlib import Path
from build import ROOT,cases

def evaluate(t,source,dest=None):
 # Run saved implementation in a separate Python interpreter; reference and cases
 # never exist in model filesystem during its turn.
 ns={};exec(t['reference'],ns);base=ns['solve']
 if t['tier']<=2: expected=[base(c) for c in cases(t)]
 elif t['tier']==3:expected=[[base(x) for x in c] for c in cases(t)]
 else:
  # Reference journal imported with canonical pipeline injected, independently of candidate.
  import types
  from dataclasses import dataclass
  @dataclass(frozen=True)
  class Result:value:object
  mods={n:sys.modules.get(n) for n in ['model','service','render']}
  for n in mods:sys.modules[n]=types.ModuleType(n)
  sys.modules['model'].Result=Result
  sys.modules['service'].compute=lambda x:Result(base(x))
  sys.modules['render'].present=lambda x:json.dumps(x.value)
  journal={};exec((ROOT/'scripts/journal_reference.py').read_text(),journal)
  expected=[json.loads(journal['run'](json.dumps(c))) for c in cases(t)]
  for n,m in mods.items():
   if m is None:sys.modules.pop(n,None)
   else:sys.modules[n]=m
 data={'inputs':cases(t),'expected':expected,'tier':t['tier'],'base':t['cases'][0],'name':t['name']}
 with tempfile.TemporaryDirectory(dir=ROOT/'private') as td:
  p=Path(td);(p/'data.json').write_text(json.dumps(data))
  code='''import sys,json,dataclasses,traceback
sys.path.insert(0,sys.argv[1])
from api import run
D=json.load(open(sys.argv[2]));fail=[];passed=0
for i,(inp,want) in enumerate(zip(D['inputs'],D['expected'])):
 try:
  got=json.loads(run(json.dumps(inp)))
  assert got==want, repr((got,want))[:800]
  # Repeat same call checks no cross-call state leak.
  assert json.loads(run(json.dumps(inp)))==want
  passed+=1
 except Exception as e:fail.append({'case':i,'error':repr(e)[:1000]})
if D['tier']>=3:
 try:
  from model import Result
  from service import compute
  from render import present
  from core import solve
  assert dataclasses.is_dataclass(Result) and Result.__dataclass_params__.frozen
  assert [x.name for x in dataclasses.fields(Result)]==['value']
  x=compute(D['base']);assert isinstance(x,Result)
  assert x.value==solve(D['base'])
  assert json.loads(present(x))==x.value
  try:x.value=None
  except dataclasses.FrozenInstanceError:pass
  else:raise AssertionError('mutable Result')
  passed+=1
 except Exception as e:fail.append({'case':'structure','error':repr(e)})
if D['name']=='refactor':
 try:
  from core import Money
  assert dataclasses.is_dataclass(Money) and Money.__dataclass_params__.frozen
  assert Money.parse('1.235').cents==124
  assert Money.parse('.005').cents==0
  assert (Money(1)+Money(2)).cents==3
  passed+=1
 except Exception as e:fail.append({'case':'Money-contract','error':repr(e)})
print(json.dumps({'passed':not fail,'checks_passed':passed,'checks_total':len(D['inputs'])+(D['tier']>=3)+(D['name']=='refactor'),'failures':fail}))
'''
  (p/'eval.py').write_text(code)
  try:
   r=subprocess.run([sys.executable,str(p/'eval.py'),str(source),str(p/'data.json')],capture_output=True,text=True,timeout=60)
  except subprocess.TimeoutExpired:
   result={'passed':False,'checks_passed':0,'checks_total':len(expected)+(t['tier']>=3)+(t['name']=='refactor'),'failures':[{'runtime':'candidate evaluator exceeded 60 seconds'}]}
   if dest:Path(dest).write_text(json.dumps(result,indent=2))
   return result
  try: result=json.loads(r.stdout)
  except Exception:result={'passed':False,'checks_passed':0,'checks_total':len(expected)+(t['tier']>=3)+(t['name']=='refactor'),'failures':[{'import':r.stderr[-2000:]}]}
  if dest:Path(dest).write_text(json.dumps(result,indent=2))
  return result
