import json, math
from pathlib import Path
import numpy as np
from scipy.stats import fisher_exact,beta
from run import ROOT

def cp(k,n,tail=.0125):
    return (0. if k==0 else float(beta.ppf(tail,k,n-k+1)),1. if k==n else float(beta.ppf(1-tail,k+1,n-k)))
def analyze(rnd):
    rs=[json.loads(p.read_text()) for p in (ROOT/'results').glob(f'r{rnd}-*/result.json')]
    groups=[]
    for m in ['gpt-6-luna','gpt-6-astra']:
        for e in ['low','high']:
            for level in ['hard','easy']:
                rows=[r for r in rs if r['model']==m and r['effort']==e and r['level']==level]
                if not rows: continue
                good=[r for r in rows if r['status']=='completed' and r['usage'] is not None and r['returncode']==0]
                costs=[]
                price=(.1,.01,.125,.5) if m.endswith('luna') else (10,1,12.5,50)
                for r in rows:
                    u=r['usage']
                    if u:
                        i=u['input_tokens']; c=u.get('cached_input_tokens',0); w=u.get('cache_write_input_tokens',0)
                        # Input includes cached and cache-write tokens; avoid charging writes twice.
                        costs.append(((i-c-w)*price[0]+c*price[1]+w*price[2]+u['output_tokens']*price[3])/1e6)
                n=len(good); k=sum(r['passed'] for r in good)
                groups.append(dict(model=m,effort=e,level=level,n=n,attempted=len(rows),passes=k,rate=k/n if n else None,ci=cp(k,n,.025) if n else [0,1],usd_task=sum(costs)/len(rows),total_usd=sum(costs)))
    a=[r for r in rs if r['model']=='gpt-6-luna' and r['effort']=='low' and r['level']=='hard']
    b=[r for r in rs if r['model']=='gpt-6-astra' and r['effort']=='high' and r['level']=='hard']
    expected=20 if rnd==1 else 40
    complete=len(a)==len(b)==expected and all(r['status']=='completed' and r['usage'] and r['returncode']==0 for r in a+b)
    stats=dict(round=rnd,complete=bool(complete),verdict='STILL INCONCLUSIVE',groups=groups)
    if complete:
        ka=sum(r['passed'] for r in a); kb=sum(r['passed'] for r in b)
        p=float(fisher_exact([[kb,len(b)-kb],[ka,len(a)-ka]],alternative='greater').pvalue)
        ids=sorted(set(r['task'] for r in a))
        ar=np.array([[r['passed'] for r in sorted(a,key=lambda r:r['rep']) if r['task']==t] for t in ids],dtype=float)
        br=np.array([[r['passed'] for r in sorted(b,key=lambda r:r['rep']) if r['task']==t] for t in ids],dtype=float)
        d=br.mean(axis=1)-ar.mean(axis=1); rng=np.random.default_rng(17)
        boot=np.quantile(d[rng.integers(0,len(d),(50000,len(d)))].mean(axis=1),[.0125,.9875])
        n=len(ids)
        lower=cp(int(np.all(br,axis=1).sum()),n)[0]-cp(int(np.any(ar,axis=1).sum()),n)[1]
        upper=cp(int(np.any(br,axis=1).sum()),n)[1]-cp(int(np.all(ar,axis=1).sum()),n)[0]
        lo=min(lower,float(boot[0])); hi=max(upper,float(boot[1])); gap=float(d.mean())
        verdict='PROVEN' if gap>=.2 and p<.025 and lo>=.2 else 'DISPROVEN' if hi<.2 else 'STILL INCONCLUSIVE'
        stats.update(verdict=verdict,gap=gap,fisher_p=p,bootstrap_ci=boot.tolist(),decision_ci=[lo,hi],task_clusters=n)
    (ROOT/'results'/f'analysis-round{rnd}.json').write_text(json.dumps(stats,indent=2))
    return stats
if __name__=='__main__':
    import sys
    s=analyze(int(sys.argv[1])); print(json.dumps(s,indent=2))
