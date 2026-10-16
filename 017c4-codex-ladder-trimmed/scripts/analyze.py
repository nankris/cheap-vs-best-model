import csv,json,math
from pathlib import Path
import numpy as np
from scipy.stats import binomtest,norm,beta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
MODELS=['gpt-6-luna','gpt-6-astra']
def analyze():
 tasks=json.loads((ROOT/'private/suite.json').read_text());rows=[json.loads(p.read_text()) for p in (ROOT/'results').glob('T*/result.json')]
 by={(r['task'],r['model'],r['rep']):r for r in rows}
 rng=np.random.default_rng(1703);stats=[]
 for tier in [3,4]:
  ts=[t for t in tasks if t['tier']==tier];complete=[t for t in ts if all((t['id'],m,r) in by for m in MODELS for r in [1])]
  if not complete:continue
  scores=np.array([[np.mean([by[t['id'],m,r]['passed'] for r in [1]]) for m in MODELS] for t in complete])
  d=scores[:,1]-scores[:,0];n=len(d)
  boot=d[rng.integers(n,size=(100000,n))].mean(1);lo,hi=np.quantile(boot,[.025,.975])
  guard=None
  if np.all(d==0):
   u=1-.05**(1/n);lo,hi=-u,u;guard='exact discordance bound'
  elif np.ptp(d)==0:
   u=math.sqrt(2*math.log(40)/n);lo,hi=max(-1,float(d.mean())-u),min(1,float(d.mean())+u);guard='Hoeffding guard'
  pos=int((d>0).sum());neg=int((d<0).sum());p=binomtest(pos,pos+neg,.5,alternative='greater').pvalue if pos+neg else 1
  reverse=binomtest(neg,pos+neg,.5,alternative='greater').pvalue if pos+neg else 1
  verdict='STILL INCONCLUSIVE'
  if n==len(ts):
   if lo>0 and p<.05:verdict='PROVEN'
   elif hi<0 and reverse<.05:verdict='DISPROVEN (reverse superiority)'
   elif lo>-.1 and hi<.1:verdict='DISPROVEN (equivalent within 10 points)'
  stats.append({'tier':tier,'complete_tasks':n,'planned_tasks':len(ts),'luna_passes':int(scores[:,0].sum()),'astra_passes':int(scores[:,1].sum()),'trials_per_arm':n,'gap':float(d.mean()),'ci95':[float(lo),float(hi)],'bootstrap_ci95':list(map(float,np.quantile(boot,[.025,.975]))),'guard':guard,'sign_positive':pos,'sign_negative':neg,'sign_p':p,'verdict':verdict})
 top=next((s for s in stats if s['tier']==4),None)
 verdict=top['verdict'] if top else 'STILL INCONCLUSIVE'
 token_totals={m:{k:sum((r.get('usage') or {}).get(k,0) for r in rows if r['model']==m) for k in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens']} for m in MODELS}
 attempts=[json.loads(p.read_text()) for p in (ROOT/'results').glob('T*/attempt-*/metadata.json')]
 infra=[r for r in attempts if r['status']!='completed']
 summary={'verdict':verdict,'completed':len(rows),'planned':48,'tiers':stats,'tokens':token_totals,'infra_attempts':len(infra),'gpu':None,'CU':0}
 (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2))
 with (ROOT/'results/trials.csv').open('w') as f:
  fields=['task','tier','name','model','effort','rep','attempt','passed','checks_passed','checks_total','seconds'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(sorted(rows,key=lambda r:(r['task'],r['model'],r['rep'])))
 # Reproduce planning assumptions without treating repetitions as tasks.
 power={'n':12,'normal_approx_power_gap40_sd45':float(norm.cdf(.4*math.sqrt(12)/.45-1.96)),'normal_approx_power_gap25_sd35':float(norm.cdf(.25*math.sqrt(12)/.35-1.96)),'zero_discordance_upper95':1-.05**(1/12),'minimum_n_zero_discordance_equivalence':29,'note':'12 tasks cannot establish 10-point equivalence under retained zero-discordance guard'}
 (ROOT/'results/power.json').write_text(json.dumps(power,indent=2))
 fig,axes=plt.subplots(1,2,figsize=(10,4.2));x=np.arange(len(stats));width=.34
 for j,m in enumerate(MODELS):
  rates=[s['luna_passes' if j==0 else 'astra_passes']/s['trials_per_arm']*100 for s in stats]
  axes[0].bar(x+(j-.5)*width,rates,width,label='Luna / low' if j==0 else 'Astra / high',color=['#227c9d','#e07a30'][j])
 axes[0].set(xticks=x,xticklabels=[f"Tier {s['tier']}\nn={s['complete_tasks']}" for s in stats],ylabel='All-tests pass rate (%)',ylim=(0,105));axes[0].legend(frameon=False)
 gaps=np.array([s['gap'] for s in stats])*100;los=np.array([s['ci95'][0] for s in stats])*100;his=np.array([s['ci95'][1] for s in stats])*100
 axes[1].axhspan(-10,10,color='#bbbbbb',alpha=.2,label='Equivalence ±10 points');axes[1].axhline(0,color='black',lw=.7)
 axes[1].errorbar(x,gaps,yerr=[gaps-los,his-gaps],fmt='o',capsize=5,color='#304b69');axes[1].set(xticks=x,xticklabels=[f"Tier {s['tier']}" for s in stats],ylabel='Astra − Luna (percentage points)');axes[1].legend(frameon=False,fontsize=8)
 fig.suptitle('Codex difficulty ladder: '+verdict);fig.tight_layout();fig.savefig(ROOT/'chart.png',dpi=180);plt.close(fig)
 table='| Tier | Paired tasks | Luna / low | Astra / high | Gap (points) | Paired 95% CI (points) |\n|---|---:|---:|---:|---:|---:|\n'
 for s in stats:table+=f"| {s['tier']} | {s['complete_tasks']}/{s['planned_tasks']} | {s['luna_passes']}/{s['trials_per_arm']} | {s['astra_passes']}/{s['trials_per_arm']} | {100*s['gap']:.1f} | [{100*s['ci95'][0]:.1f}, {100*s['ci95'][1]:.1f}] |\n"
 breakpoint=next((s['tier'] for s in stats if s['gap']>.20),None)
 elapsed=(__import__('time').time()-json.loads((ROOT/'results/start.json').read_text())['started'])/60
 text=f'''# 017c4 — trimmed Codex difficulty ladder

**Verdict: {verdict}.** Tier 4 is primary: gpt-6-astra/high minus gpt-6-luna/low. {len(rows)}/48 evaluable fresh trials completed, {len(infra)} infrastructure attempts. Elapsed wall time at analysis: {elapsed:.1f} minutes. GPU: none; CU used: **0**. No Colab session started, none to stop.

{table}

Each task has one fresh call per arm. Paired task percentile bootstrap: 100,000 resamples, seed 1703. Exact one-sided task sign p={top['sign_p'] if top else 'unavailable'}. The primary rule requires positive lower CI plus sign p<.05 for superiority; reverse superiority or an entire CI inside ±10 points disproves the hypothesis. Constant-zero outcomes use the inherited exact discordance bound; constant-nonzero outcomes use the inherited Hoeffding guard. See results/summary.json for unguarded bootstrap intervals, guard, and discordance counts.

The fixed sample is 12 tasks per tier. Round 3 had only five tier-3 tasks: seven additional batch tasks reuse its first seven top-tier algorithms and unchanged batch template. Tier 4 retains its first 12 tasks in original order; no historical outcomes are pooled. All 24 references pass and all 24 deliberately broken starters fail. Filesystem isolation probe denies hidden suite access and unmounting its cover. Source snapshots are graded after each call, using the unchanged inherited grader, algorithm oracles, repeated calls and Result contract checks. Results and raw events checkpoint directly to local disk on every completion; retries preserve infrastructure logs and do not convert service failures into model failures.

The user-fixed sample cannot guarantee a conclusive verdict under the user-fixed rule. In particular, zero tier-4 discordances at n=12 give an exact upper bound of {100*(1-.05**(1/12)):.2f}%, exceeding the 10-point margin; at least 29 tasks would be required. A zero-width raw bootstrap at a ceiling is not evidence of equivalence. If neither rule holds, STILL INCONCLUSIVE means the fixed sampling budget is exhausted; the reported elapsed time distinguishes this from wall-time exhaustion. No post-hoc margin changes or extra tasks were used. Planning assumptions and power are in results/power.json.

These are purposive synthetic Python algorithms sharing journal machinery, so exchangeable-task bootstrap assumptions limit population generalization. Algorithms overlap across tiers; tier 3 is descriptive only. The contrast bundles model and effort. One repetition cannot characterize within-task generation variance. No production-wide ranking or difficulty breakpoint is established by these two tiers.

Reproduce with scripts/validate.py, scripts/run.py (resumable, four workers), and scripts/analyze.py under /workspace/tools/mlenv/bin/python. private/suite.json is the frozen selected suite; inherited build.py is only a fixture/helper library and should not regenerate the untrimmed suite. Raw per-call events, stderr, invocation, metadata, source snapshots and grading are under results/T*/; results/trials.csv is the analysis table. Default Codex account only; inherited CODEX_HOME was already set by the environment and never changed. Original and round-3 folders were read only. No Claude, Grok, GPU, or network data was needed. Local git only; never pushed.
'''
 (ROOT/'writeup.md').write_text(text)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':analyze()
