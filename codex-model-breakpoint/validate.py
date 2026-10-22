import json, subprocess, sys, tempfile, shutil
from pathlib import Path
from run import ROOT, fixture, hidden

def validate(suite='suite.json'):
    out=[]
    for t in json.loads((ROOT/suite).read_text()):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'repo'; p.mkdir(); fixture(t,p)
            (p/'codec.py').write_text('import json\ndef decode(s): return json.loads(s)\n')
            (p/'core.py').write_text(t['reference'])
            (p/'service.py').write_text('from core import solve\ndef compute(rows): return solve(rows)\n' if t['name']!='refactor' else 'from core import Money\ndef compute(rows):\n m=Money(0)\n for s in rows: m=m+Money.parse(s)\n return m\n')
            (p/'render.py').write_text('import json\ndef present(v): return json.dumps(v)\n' if t['name']!='refactor' else 'def present(v): return ("-" if v.cents<0 else "")+str(abs(v.cents)//100)+"."+str(abs(v.cents)%100).zfill(2)\n')
            if t['name']=='refactor': (p/'api.py').write_text('import json\nfrom codec import decode\nfrom service import compute\nfrom render import present\ndef run(s): return json.dumps(present(compute(decode(s))))\n')
            test=Path(d)/'test_hidden.py'; test.write_text(hidden(t,p))
            r=subprocess.run([sys.executable,'-m','pytest','-q',str(test)],capture_output=True,text=True)
            out.append(dict(task=t['id'],passed=r.returncode==0,output=r.stdout+r.stderr))
    (ROOT/'results'/('reference-validation-'+suite)).write_text(json.dumps(out,indent=2))
    assert all(r['passed'] for r in out), [(r['task'],r['output']) for r in out if not r['passed']]
    print('Reference validated',len(out))

def rescore():
    tasks={t['id']:t for s in ['suite.json','suite2.json'] if (ROOT/s).exists() for t in json.loads((ROOT/s).read_text())}
    for f in sorted((ROOT/'results').glob('r*/result.json')):
        r=json.loads(f.read_text()); dest=f.parent
        if 'No module named pytest' not in (dest/'tests.txt').read_text(): continue
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'repo'; shutil.copytree(dest/'solution',p)
            test=Path(d)/'test_hidden.py'; test.write_text(hidden(tasks[r['task']],p))
            q=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(test)],capture_output=True,text=True)
            shutil.copy(dest/'tests.txt',dest/'tests-initial-infrastructure-error.txt')
            (dest/'tests.txt').write_text(q.stdout+q.stderr)
            r['passed']=q.returncode==0; r['rescored']='Unchanged saved solution; evaluator pytest installed after initial call.'
            f.write_text(json.dumps(r,indent=2)); print('Rescored',dest.name,r['passed'])
if __name__=='__main__':
    validate(sys.argv[1] if len(sys.argv)>1 else 'suite.json'); rescore()
