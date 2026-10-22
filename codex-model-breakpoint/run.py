import concurrent.futures as cf, json, os, random, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from build_suite import ROOT, build

def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s)
def fixture(t,p):
    write(p/'TASK.md',t['spec']+'\nAPI: api.run(payload: str) -> str. Payload and result are JSON. Fix the chained modules; standard library only. Do not change the API.\n')
    write(p/'codec.py','import json\ndef decode(payload):\n    return payload.split(",")\n')
    write(p/'core.py','def solve(rows):\n    return rows[0] if rows else 0\n')
    write(p/'service.py','from core import solve\ndef compute(rows):\n    return solve(rows[::-1])\n')
    write(p/'render.py','def present(value):\n    return str(value)\n')
    write(p/'api.py','from codec import decode\nfrom service import compute\nfrom render import present\ndef run(payload):\n    return present(compute(decode(payload)))\n')
    if t['name']=='refactor':
        write(p/'core.py','def solve(rows):\n    return sum(float(x) for x in rows)\n')
    subprocess.run(['git','init','-q',str(p)],check=True)
    subprocess.run(['git','-C',str(p),'add','.'],check=True)
    subprocess.run(['git','-C',str(p),'-c','user.name=Experiment','-c','user.email=experiment@example.invalid','commit','-qm','fixture'],check=True)

def hidden(t,p):
    ns={}; exec(t['reference'],ns)
    expected=[ns['solve'](c) for c in t['cases']]
    code='import sys,json\nsys.path.insert(0,'+repr(str(p))+')\nfrom api import run\n'
    code+='CASES='+repr(list(zip(t['cases'],expected)))+'\n'
    code+='import pytest\n@pytest.mark.parametrize("rows,expected",CASES)\ndef test_api(rows,expected):\n    before=json.dumps(rows,sort_keys=True)\n    assert json.loads(run(json.dumps(rows))) == expected\n    assert json.dumps(rows,sort_keys=True)==before\n'
    if t['name']=='refactor':
        code+='def test_structure():\n    from core import Money\n    from service import compute\n    from render import present\n    from dataclasses import FrozenInstanceError\n    m=Money.parse("1.235")\n    assert m.cents==124\n    assert isinstance(compute([".01"]),Money)\n    assert present(Money(-1))=="-0.01"\n    assert (Money(1)+Money(2)).cents==3\n    with pytest.raises(FrozenInstanceError): m.cents=2\n'
    return code

def execute(job):
    rnd,t,model,effort,rep=job; key=f'r{rnd}-{t["id"]}-{model}-{effort}-{rep}'
    dest=ROOT/'results'/key; result=dest/'result.json'
    if result.exists(): return json.loads(result.read_text())
    dest.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='codex-breakpoint-') as tmp:
        p=Path(tmp)/'repo'; p.mkdir(); fixture(t,p)
        prompt='Read TASK.md and repair the implementation. Work only in this repository. Do not use subagents, network or inspect files outside the repository. Validate with your own tests. Finish after implementing the requested behavior.'
        cmd=['codex','exec','--ignore-user-config','--ephemeral','--json','--skip-git-repo-check','--dangerously-bypass-approvals-and-sandbox','-m',model,'-c',f'model_reasoning_effort="{effort}"','-C',str(p),prompt]
        start=time.time(); status='completed'; rc=None
        with open(dest/'events.jsonl','w') as out,open(dest/'stderr.txt','w') as err:
            proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            try: rc=proc.wait(timeout=240)
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(proc.pid,signal.SIGTERM); proc.wait(); status='timeout'
        events=[]
        for line in (dest/'events.jsonl').read_text().splitlines():
            try: events.append(json.loads(line))
            except ValueError: pass
        usage=[e['usage'] for e in events if e.get('type')=='turn.completed']
        if not usage: status='infrastructure_missing_usage' if status!='timeout' else status
        testfile=Path(tmp)/'test_hidden.py'; testfile.write_text(hidden(t,p))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        test=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(testfile)],cwd=p,env=env,capture_output=True,text=True,timeout=30)
        write(dest/'tests.txt',test.stdout+test.stderr)
        diff=subprocess.run(['git','-C',str(p),'diff'],capture_output=True,text=True).stdout
        write(dest/'patch.diff',diff)
        # Preserve all produced source, including newly added files.
        for f in p.rglob('*.py'):
            if '.git' not in f.parts: write(dest/'solution'/f.relative_to(p),f.read_text())
        r=dict(round=rnd,task=t['id'],level=t['level'],model=model,effort=effort,rep=rep,status=status,returncode=rc,passed=test.returncode==0,seconds=round(time.time()-start,2),usage=usage[-1] if usage else None)
        write(result,json.dumps(r,indent=2)); print(key,status,r['passed'],flush=True); return r

def main(rnd):
    if not (ROOT/'suite.json').exists(): build()
    tasks=json.loads((ROOT/('suite.json' if rnd==1 else 'suite2.json')).read_text())
    jobs=[(rnd,t,m,e,r) for t in tasks for m in ['gpt-6-luna','gpt-6-astra'] for e in ['low','high'] for r in [1,2]]
    random.Random(17+rnd).shuffle(jobs)
    with cf.ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(execute,jobs))
if __name__=='__main__': main(int(sys.argv[1]))
