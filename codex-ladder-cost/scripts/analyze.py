"""Fixed paired bootstrap and descriptive exact pass intervals; no optional stopping."""
from pathlib import Path
import json,math,csv
import numpy as np
from scipy.stats import beta,norm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
rows=[json.loads(p.read_text()) for p in sorted((ROOT/'results').glob('T*/result.json'))]
by={(r['task'],r['model']):r for r in rows}
suite=json.loads((ROOT/'private/suite.json').read_text())
pairs=[(t,by[t['id'],'gpt-6-astra'],by[t['id'],'gpt-6-luna']) for t in suite if (t['id'],'gpt-6-astra') in by and (t['id'],'gpt-6-luna') in by]
def tokens(r,reasoning=True):
 u=r['usage'];return u['input_tokens']+u['output_tokens']+(u.get('reasoning_output_tokens',0) if reasoning else 0)
def estimate(vals):
 x=np.log(vals);rng=np.random.default_rng(1705)
 boot=np.exp(x[rng.integers(0,len(x),size=(20000,len(x)))].mean(axis=1))
 return {'geometric_mean_ratio':float(np.exp(x.mean())),'ci95':np.quantile(boot,[.025,.975]).tolist(),'paired_log_sd':float(x.std(ddof=1))}
summary={'complete_trials':len(rows),'paired_tasks':len(pairs),'seed':1705,'resamples':20000,'gpu':None,'cu_used':0}
metrics={}
if pairs:
 for name,fn in [('total_tokens',tokens),('input_plus_output',lambda r:tokens(r,False)),('wall_seconds',lambda r:r['seconds'])]:
  metrics[name]=estimate([fn(a)/fn(l) for t,a,l in pairs])
summary['metrics']=metrics
summary['verdict']='STILL INCONCLUSIVE'
if len(pairs)==24:
 lo,hi=metrics['total_tokens']['ci95']
 if lo>1.25:summary['verdict']='PROVEN'
 elif hi<1.25:summary['verdict']='DISPROVEN'
summary['pass_rates']={}
for model in ['gpt-6-astra','gpt-6-luna']:
 rr=[r for r in rows if r['model']==model];n=len(rr);k=sum(r['passed'] for r in rr)
 ci=[float(beta.ppf(.025,k,n-k+1)) if k else 0.,float(beta.ppf(.975,k+1,n-k)) if k<n else 1.]
 summary['pass_rates'][model]={'passed':k,'n':n,'exact_ci95':ci,'failures':[r['task'] for r in rr if not r['passed']]}
(ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2))
with (ROOT/'results/trials.csv').open('w') as f:
 fields=['task','tier','model','effort','passed','seconds','input_tokens','output_tokens','reasoning_output_tokens','total_tokens'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for r in rows:w.writerow({**{k:r[k] for k in fields[:6]},**{k:r['usage'].get(k,0) for k in fields[6:9]},'total_tokens':tokens(r)})
with (ROOT/'results/pairs.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['task','tier','astra_tokens','luna_tokens','token_ratio','astra_seconds','luna_seconds','wall_ratio'])
 for t,a,l in pairs:w.writerow([t['id'],t['tier'],tokens(a),tokens(l),tokens(a)/tokens(l),a['seconds'],l['seconds'],a['seconds']/l['seconds']])
lines=['# Codex ladder token cost','',f"**Verdict: {summary['verdict']}.** Completed {len(rows)}/48 trials, {len(pairs)}/24 paired tasks. GPU: none; CU used: 0.",'','| Metric (Astra/high ÷ Luna/low) | Geometric mean | Paired bootstrap 95% CI |','|---|---:|---:|']
for name,m in metrics.items():lines.append(f"| {name} | {m['geometric_mean_ratio']:.3f} | [{m['ci95'][0]:.3f}, {m['ci95'][1]:.3f}] |")
lines+=['','Primary rule fixed before calls: PROVEN if the total-token CI lies entirely above 1.25; DISPROVEN if entirely below 1.25. Paired percentile bootstrap, 20,000 resamples, seed 1705. Total includes input + output + separately reported reasoning; input+output sensitivity is also shown. Wall time is secondary. Tokens measure resource use, not dollars.','', '| Arm | All-tests pass | Exact 95% CI | Failing tasks |','|---|---:|---:|---|']
for model,r in summary['pass_rates'].items():lines.append(f"| {model} | {r['passed']}/{r['n']} | [{100*r['exact_ci95'][0]:.1f}%, {100*r['exact_ci95'][1]:.1f}%] | {', '.join(r['failures']) or 'none'} |")
lines+=['','One fresh run per arm per task; no old outcomes pooled. Fixed 12 tier-3 and 12 tier-4 tasks copied from the [trimmed ladder](../codex-ladder-trimmed/). Inherited hidden grader and mount isolation protect the suite during generation. Reference validation and deliberate broken-fixture rejection are in results/validation.json. Raw JSONL events, stderr, invocation, snapshots and grading are saved per attempt. Attempts ledger persists starts and completions.','', 'Limits: purposive synthetic algorithms share machinery and overlap across tiers; task bootstrap assumes exchangeability and cannot establish a production-wide ranking. One run per configuration does not estimate generation variance. Token accounting includes cached input and the requested separate reasoning field. Wall ratios may reflect concurrent service load. The comparison bundles model and effort. README.md contains the prospective power assumptions, fixed budget and full decision rule.','', 'Reproduce with scripts/validate.py, scripts/run.py (resumable), scripts/analyze.py. results/trials.csv and pairs.csv contain the analysis inputs; results/summary.json contains unrounded estimates.']
(ROOT/'writeup.md').write_text('\n'.join(lines)+'\n')
fig,axes=plt.subplots(1,2,figsize=(11,4.5))
for ax,name,title,fn in [(axes[0],'total_tokens','Total token ratio',tokens),(axes[1],'wall_seconds','Wall-clock ratio',lambda r:r['seconds'])]:
 if pairs:
  vals=[fn(a)/fn(l) for t,a,l in pairs];ax.scatter(range(len(vals)),vals,c=['#4477aa' if t['tier']==3 else '#ee7733' for t,a,l in pairs],s=25)
  m=metrics[name];ax.axhline(m['geometric_mean_ratio'],color='black',label='Geometric mean');ax.axhspan(*m['ci95'],color='gray',alpha=.2,label='Paired 95% CI')
 ax.axhline(1.25,color='red',linestyle='--',label='1.25 threshold');ax.axhline(1,color='gray',linestyle=':');ax.set_yscale('log');ax.set_title(title);ax.set_xlabel('Fixed task order (blue tier 3; orange tier 4)');ax.set_ylabel('Astra/high ÷ Luna/low')
axes[0].legend(fontsize=8);fig.suptitle(f"Codex ladder token cost: {summary['verdict']} ({len(pairs)}/24 pairs)");fig.tight_layout();fig.savefig(ROOT/'chart.png',dpi=170);plt.close(fig)
print(json.dumps(summary,indent=2))
