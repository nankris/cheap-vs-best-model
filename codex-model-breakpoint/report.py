import csv,json,statistics
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run import ROOT
from analyze import analyze,cp

def main():
    rounds=[analyze(i) for i in [1,2] if list((ROOT/'results').glob(f'r{i}-*/result.json'))]
    rows=[json.loads(p.read_text()) for p in sorted((ROOT/'results').glob('r*/result.json'))]
    flat=[]
    for r in rows:
        f={k:v for k,v in r.items() if k!='usage'}; f.update(r['usage'] or {}); flat.append(f)
    cols=sorted(set(k for r in flat for k in r))
    with open(ROOT/'results/runs.csv','w') as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(flat)
    verdict=rounds[-1]['verdict']
    text=['# Codex model breakpoint','',f'**Verdict: {verdict}.** Hypothesis: cheap-low trails strong-high by at least 20 percentage points on hard tasks.','',
    'This is an evaluation of original synthetic Python tasks, not a production-repository benchmark. Round 1 has ten hard and five easy tasks; round 2, if activated, has twenty new hard tasks and more hidden boundary cases. Each task crosses JSON decoding, service orchestration, core logic and rendering; one round-1 task explicitly requires a frozen Money dataclass across modules. Each arm gets two fresh git repository copies per task. Models see the specification and broken implementation; hidden tests and reference implementations live outside their working directory. Agents were instructed to stay inside it; this is instruction-based withholding, not filesystem-enforced isolation. No test-directed adaptation after model outcomes.','',
    '## Results','', '| Round | Arm | Set | Passes / evaluable trials | Task-cluster conservative 95% interval | API-equivalent $/attempt |', '|---|---|---|---:|---:|---:|']
    for a in rounds:
        for g in a['groups']:
            armrows=[r for r in rows if r['round']==a['round'] and r['model']==g['model'] and r['effort']==g['effort'] and r['level']==g['level'] and r['status']=='completed' and r['usage'] and r['returncode']==0]
            ids=sorted(set(r['task'] for r in armrows)); clusters=[[r['passed'] for r in armrows if r['task']==i] for i in ids]
            if clusters and all(len(c)==2 for c in clusters):
                ci=(cp(sum(all(c) for c in clusters),len(clusters),.025)[0],cp(sum(any(c) for c in clusters),len(clusters),.025)[1])
            else: ci=(0,1)
            g['cluster_ci']=ci
            text.append(f"| {a['round']} | {g['model']} / {g['effort']} | {g['level']} | {g['passes']}/{g['n']} ({g['attempted']} attempted) | {100*ci[0]:.1f}–{100*ci[1]:.1f}% | ${g['usd_task']:.5f} |")
        text+=['',f"Round {a['round']}: **{a['verdict']}**."]
        if a['complete']:
            lo,hi=a['decision_ci']; bl,bh=a['bootstrap_ci']
            text += [f"Strong-high minus cheap-low: **{100*a['gap']:.1f} points**, decision interval **[{100*lo:.2f}, {100*hi:.2f}] points**; paired task-bootstrap interval [{100*bl:.2f}, {100*bh:.2f}] points; one-sided Fisher p={a['fisher_p']:.6g}. {a['task_clusters']} task clusters, two repetitions each."]
        else: text+=['The planned primary comparison is incomplete; missing calls cannot be scored as model failures.']
    text+=['','## Decision and interpretation','',
    'The preregistered rule requires a >=20-point observed gap, Fisher p<0.025 and a conservative 97.5% decision lower bound >=20 points to prove the claim. An upper bound below 20 disproves this effect size. The decision interval uses the wider of a 50,000-resample paired task-cluster bootstrap and conservative task-level exact binomial bounds. For lower bounds, a task succeeds only if both repetitions pass; upper bounds use either repetition passing. This brackets the per-repetition success rate without assuming independent repeats. Fisher treats trials independently, so its p-value alone cannot establish the verdict. Each of two rounds has a 0.025 error allocation; no pooled post-hoc test is substituted.','',
    'At a perfect ceiling the bootstrap is degenerate and Fisher p=1; neither proves equivalence. The exact boundary guard keeps the ten-task first round inconclusive at a ceiling. Twenty independent constructed tasks can bound an unobserved cheap-model failure probability below 20%. This inference assumes task clusters are exchangeable; task selection was synthetic and purposive, so conclusions are limited to this suite/design. A result against a 20-point deficit does not establish equal models or locate a general coding breakpoint.','',
    '## Cost, compute and reproducibility','']
    total=sum(g['total_usd'] for a in rounds for g in a['groups'])
    text += [f"{len(rows)} experimental calls; API-equivalent task total **${total:.5f}**, excluding two availability probes. Mean runtime {statistics.mean(r['seconds'] for r in rows):.1f}s per attempt. GPU: **none**. Compute used: **0 CU**.",'',
    'API-equivalent rates per million uncached / cached / cache-write / output tokens: Luna $0.10 / $0.01 / $0.125 / $0.50; Astra $10 / $1 / $12.50 / $50. Uncached input = input minus cached minus cache-write tokens. Reasoning output is part of output and is not double-counted. Standard short-context rates from [official OpenAI pricing](https://developers.openai.com/api/docs/pricing), accessed 2026-10-15. This is token accounting at list price, not a measured subscription bill. The Codex account was shared with other work running at the same time, so cache and latency behavior are descriptive.','',
    'Runner: `python build_suite.py; python run.py 1`; after its completion `python controller.py` performs the conditional second round. `python report.py` regenerates results/runs.csv, writeup and chart. Saved result.json files prevent repeating completed calls. Python dependencies are pinned in requirements.txt. CLI help and selected local model catalog metadata are recorded under results/. No private data or credentials are required to reproduce the synthetic suite.','',
    'Procedural deviation: reference validation finished after launching the first-round calls, though before most results. The first completed call was initially graded without pytest; it was regraded from its unchanged saved source after installing pytest, and its original evaluator error is retained. All first-round and second-round references pass the same evaluator. Reference syntax for glob and signed-denominator rational parsing were corrected during second-round preparation before any second-round model call. Twenty-two independent hand-computed oracle checks passed. Shuffle seeds were 18 and 19 (17+round), rather than literal 17 stated initially. These are evaluator repairs, not model retries.','',
    'Raw JSONL events include terminal token usage. Each result has test output, patch and all generated Python source. Infrastructure errors/timeouts are missing for primary inference, not wrong answers. The two-round maximum is enforced; no further redesign is allowed.']
    (ROOT/'writeup.md').write_text('\n'.join(text)+'\n')
    fig,axes=plt.subplots(1,len(rounds)+1,figsize=(6*(len(rounds)+1),4.8))
    colors=['#4383c3','#80b5dc','#e39b37','#d46928']
    for ax,a in zip(axes,rounds):
        gs=[g for g in a['groups'] if g['level']=='hard']; xs=np.arange(len(gs)); ys=np.array([g['rate'] or 0 for g in gs])*100
        lows=np.array([g['cluster_ci'][0] for g in gs])*100; highs=np.array([g['cluster_ci'][1] for g in gs])*100
        ax.bar(xs,ys,color=colors[:len(gs)]); ax.errorbar(xs,ys,yerr=[ys-lows,highs-ys],fmt='none',color='black',capsize=4)
        ax.set_xticks(xs,[g['model'].removeprefix('gpt-6-')+'\n'+g['effort'] for g in gs]); ax.set_ylim(0,108); ax.set_ylabel('Hard-task pass rate (%)'); ax.set_title(f"Round {a['round']}: {a['verdict']}")
        for x,y,g in zip(xs,ys,gs): ax.text(x,y+2,f"{g['passes']}/{g['n']}",ha='center')
    ax=axes[-1]; a=rounds[-1]; gs=[g for g in a['groups'] if g['level']=='hard']; xs=np.arange(len(gs)); costs=[g['usd_task'] for g in gs]
    ax.bar(xs,costs,color=colors[:len(gs)]); ax.set_yscale('log'); ax.set_xticks(xs,[g['model'].removeprefix('gpt-6-')+'\n'+g['effort'] for g in gs]); ax.set_ylabel('API-equivalent $ / task (log)'); ax.set_title(f"Round {a['round']} token-accounting cost")
    for x,v in zip(xs,costs): ax.text(x,v*1.15,f'${v:.4f}',ha='center')
    ax.set_ylim(min(costs)*.5,max(costs)*3)
    fig.suptitle('Codex model breakpoint — 2 fresh copies per task'); fig.tight_layout(); fig.savefig(ROOT/'chart.png',dpi=160); plt.close(fig)
    print(verdict,'calls',len(rows),'API-equivalent',total)
if __name__=='__main__': main()
