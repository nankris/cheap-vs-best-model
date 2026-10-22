"""Resumable paired trial runner, raw attempts durable before grading."""
import concurrent.futures as cf,json,os,random,signal,subprocess,sys,tempfile,time,shutil,re
from pathlib import Path
from build import ROOT,fixture
from grade import evaluate
ARMS=[('gpt-6-luna','low'),('gpt-6-astra','high')]
START=ROOT/'results/start.json'

def atomic(p,obj):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2));tmp.replace(p)

def execute(job,deadline):
 t,model,effort,rep=job;key=f'{t["id"]}-{model}-{effort}-{rep}';dest=ROOT/'results'/key;dest.mkdir(exist_ok=True)
 if (dest/'result.json').exists():return
 attempt=1
 while time.time()<deadline:
  ad=dest/f'attempt-{attempt}'
  if ad.exists():attempt+=1;continue
  ad.mkdir();start=time.time()
  with tempfile.TemporaryDirectory(prefix='codex-ladder-trimmed-') as td:
   p=Path(td);fixture(t,p)
   prompt='Read TASK.md and implement the complete contract. Work only in this workspace. Do not use subagents or network or inspect other directories. You may create your own tests. Finish after implementation and validation.'
   cmd=[sys.executable,str(ROOT/'scripts/isolate.py'),str(p),'codex','exec','--ignore-user-config','--ephemeral','--json','--skip-git-repo-check','--dangerously-bypass-approvals-and-sandbox','-m',model,'-c',f'model_reasoning_effort="{effort}"','-C',str(p),prompt]
   atomic(ad/'invocation.json',{'command':cmd,'start':start})
   with (ad/'events.jsonl').open('w') as out,(ad/'stderr.txt').open('w') as err:
    proc=subprocess.Popen(cmd,stdout=out,stderr=err,stdin=subprocess.DEVNULL,start_new_session=True)
    try:rc=proc.wait(timeout=max(1,min(600,deadline-time.time())))
    except subprocess.TimeoutExpired:
     os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(timeout=10)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
     rc=-999
   events=[]
   for line in (ad/'events.jsonl').read_text().splitlines():
    try:events.append(json.loads(line))
    except ValueError:pass
   usage=[e['usage'] for e in events if e.get('type')=='turn.completed']
   errors=[e for e in events if e.get('type') in ['error','turn.failed']]
   # Preserve candidate artifacts on both infrastructure and completed attempts.
   src=ad/'solution';src.mkdir()
   for f in p.rglob('*'):
    if f.is_file() and '.git' not in f.parts and '__pycache__' not in f.parts:
     rel=f.relative_to(p)
     if f.stat().st_size<2000000:
      (src/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,src/rel)
   good=rc==0 and bool(usage) and not errors
   meta={'task':t['id'],'tier':t['tier'],'name':t['name'],'model':model,'effort':effort,'rep':rep,'attempt':attempt,'status':'completed' if good else 'infrastructure','returncode':rc,'seconds':time.time()-start,'usage':usage[-1] if usage else None,'errors':errors}
   atomic(ad/'metadata.json',meta)
   if good:
    meta.update(evaluate(t,src,ad/'grading.json'));atomic(dest/'result.json',meta)
    print(key,'PASS' if meta['passed'] else 'FAIL',round(meta['seconds'],1),flush=True)
    return
   message=(ad/'events.jsonl').read_text()+(ad/'stderr.txt').read_text()
   # Quota messages can give an absolute epoch or reset text; preserve verbatim and
   # poll no faster than once a minute when no machine-readable reset is supplied.
   reset=re.search(r'"resets_at"\s*:\s*(\d+)',message)
   wait=max(60,float(reset.group(1))-time.time()+5) if reset else 60
   atomic(ad/'retry.json',{'wait_seconds':wait,'quota':bool(re.search('usage.limit|quota|rate.limit',message,re.I))})
   print(key,'INFRA RETRY',attempt,'wait',round(wait),flush=True)
  while wait>0 and time.time()<deadline:
   step=min(60,wait,max(0,deadline-time.time()));time.sleep(step);wait-=step
  attempt+=1
 print(key,'BUDGET_EXHAUSTED',flush=True)

def main():
 if not START.exists():atomic(START,{'started':time.time(),'deadline':time.time()+3*3600})
 deadline=json.loads(START.read_text())['deadline']
 tasks=json.loads((ROOT/'private/suite.json').read_text())
 jobs=[(t,m,e,r) for t in tasks for m,e in ARMS for r in [1]]
 random.Random(1703).shuffle(jobs)
 atomic(ROOT/'results/schedule.json',[{'task':t['id'],'model':m,'effort':e,'rep':r} for t,m,e,r in jobs])
 with cf.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda j:execute(j,deadline),jobs))
if __name__=='__main__':main()
