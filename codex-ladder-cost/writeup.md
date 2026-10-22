# Codex ladder token cost

**Verdict: STILL INCONCLUSIVE.** Completed 8/48 trials, 0/24 paired tasks. GPU: none; CU used: 0.

| Metric (Astra/high ÷ Luna/low) | Geometric mean | Paired bootstrap 95% CI |
|---|---:|---:|

Primary rule fixed before calls: PROVEN if the total-token CI lies entirely above 1.25; DISPROVEN if entirely below 1.25. Paired percentile bootstrap, 20,000 resamples, seed 1705. Total includes input + output + separately reported reasoning; input+output sensitivity is also shown. Wall time is secondary. Tokens measure resource use, not dollars.

| Arm | All-tests pass | Exact 95% CI | Failing tasks |
|---|---:|---:|---|
| gpt-6-astra | 1/1 | [2.5%, 100.0%] | none |
| gpt-6-luna | 6/7 | [42.1%, 99.6%] | T14 |

One fresh run per arm per task; no old outcomes pooled. Fixed 12 tier-3 and 12 tier-4 tasks copied from the [trimmed ladder](../codex-ladder-trimmed/). Inherited hidden grader and mount isolation protect the suite during generation. Reference validation and deliberate broken-fixture rejection are in results/validation.json. Raw JSONL events, stderr, invocation, snapshots and grading are saved per attempt. Attempts ledger persists starts and completions.

Limits: purposive synthetic algorithms share machinery and overlap across tiers; task bootstrap assumes exchangeability and cannot establish a production-wide ranking. One run per configuration does not estimate generation variance. Token accounting includes cached input and the requested separate reasoning field. Wall ratios may reflect concurrent service load. The comparison bundles model and effort. README.md contains the prospective power assumptions, fixed budget and full decision rule.

Reproduce with scripts/validate.py, scripts/run.py (resumable), scripts/analyze.py. results/trials.csv and pairs.csv contain the analysis inputs; results/summary.json contains unrounded estimates.
