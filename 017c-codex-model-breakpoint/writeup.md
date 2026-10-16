# 017c — Codex model breakpoint

**Verdict: STILL INCONCLUSIVE.** Hypothesis: cheap-low trails strong-high by at least 20 percentage points on hard tasks.

This is an evaluation of original synthetic Python tasks, not a production-repository benchmark. Round 1 has ten hard and five easy tasks; round 2, if activated, has twenty new hard tasks and more hidden boundary cases. Each task crosses JSON decoding, service orchestration, core logic and rendering; one round-1 task explicitly requires a frozen Money dataclass across modules. Each arm gets two fresh git repository copies per task. Models see the specification and broken implementation; hidden tests and reference implementations live outside their working directory. Agents were instructed to stay inside it; this is instruction-based withholding, not filesystem-enforced isolation. No test-directed adaptation after model outcomes.

## Results

| Round | Arm | Set | Passes / evaluable trials | Task-cluster conservative 95% interval | API-equivalent $/attempt |
|---|---|---|---:|---:|---:|
| 1 | gpt-6-luna / low | hard | 10/10 (10 attempted) | 0.0–100.0% | $0.00268 |
| 1 | gpt-6-luna / low | easy | 1/2 (2 attempted) | 0.0–100.0% | $0.00174 |
| 1 | gpt-6-luna / high | hard | 9/9 (9 attempted) | 0.0–100.0% | $0.00314 |
| 1 | gpt-6-luna / high | easy | 7/7 (7 attempted) | 0.0–100.0% | $0.00221 |
| 1 | gpt-6-astra / low | hard | 8/8 (8 attempted) | 0.0–100.0% | $0.22197 |
| 1 | gpt-6-astra / low | easy | 3/3 (3 attempted) | 0.0–100.0% | $0.24157 |
| 1 | gpt-6-astra / high | hard | 8/8 (8 attempted) | 0.0–100.0% | $0.26621 |
| 1 | gpt-6-astra / high | easy | 2/2 (2 attempted) | 0.0–100.0% | $0.17642 |

Round 1: **STILL INCONCLUSIVE**.
The planned primary comparison is incomplete; missing calls cannot be scored as model failures.

## Decision and interpretation

The preregistered rule requires a >=20-point observed gap, Fisher p<0.025 and a conservative 97.5% decision lower bound >=20 points to prove the claim. An upper bound below 20 disproves this effect size. The decision interval uses the wider of a 50,000-resample paired task-cluster bootstrap and conservative task-level exact binomial bounds. For lower bounds, a task succeeds only if both repetitions pass; upper bounds use either repetition passing. This brackets the per-repetition success rate without assuming independent repeats. Fisher treats trials independently, so its p-value alone cannot establish the verdict. Each of two rounds has a 0.025 error allocation; no pooled post-hoc test is substituted.

At a perfect ceiling the bootstrap is degenerate and Fisher p=1; neither proves equivalence. The exact boundary guard keeps the ten-task first round inconclusive at a ceiling. Twenty independent constructed tasks can bound an unobserved cheap-model failure probability below 20%. This inference assumes task clusters are exchangeable; task selection was synthetic and purposive, so conclusions are limited to this suite/design. A result against a 20-point deficit does not establish equal models or locate a general coding breakpoint.

## Cost, compute and reproducibility

49 experimental calls; API-equivalent task total **$5.05698**, excluding two availability probes. Mean runtime 41.6s per attempt. GPU: **none**. Experiment Colab usage: **0 CU**; no session created, so no owned session to stop. Before balance 178.23 CU. See results/colab-after.txt for the final shared balance; other assignments' consumption is not attributed to this experiment.

API-equivalent rates per million uncached / cached / cache-write / output tokens: Luna $0.10 / $0.01 / $0.125 / $0.50; Astra $10 / $1 / $12.50 / $50. Uncached input = input minus cached minus cache-write tokens. Reasoning output is part of output and is not double-counted. Standard short-context rates from [official OpenAI pricing](https://developers.openai.com/api/docs/pricing), accessed 2026-10-15. This is token accounting at list price, not a measured subscription bill. Other concurrent experiments share the account; prices and cache/latency behavior are descriptive.

Runner: `source /workspace/tools/setup.sh; python build_suite.py; python run.py 1`; after its completion `python controller.py` performs the conditional second round. `python report.py` regenerates results/runs.csv, writeup and chart. Saved result.json files prevent repeating completed calls. Python dependencies are pinned in requirements.txt. CLI help and selected local model catalog metadata are recorded under results/. No private data or credentials are required to reproduce the synthetic suite.

Procedural deviation: reference validation finished after launching the first-round calls, though before most results. The first completed call was initially graded without pytest; it was regraded from its unchanged saved source after installing pytest, and its original evaluator error is retained. All first-round and second-round references pass the same evaluator. Reference syntax for glob and signed-denominator rational parsing were corrected during second-round preparation before any second-round model call. Twenty-two independent hand-computed oracle checks passed. Shuffle seeds were 18 and 19 (17+round), rather than literal 17 stated initially. These are evaluator repairs, not model retries.

Raw JSONL events include terminal token usage. Each result has test output, patch and all generated Python source. Infrastructure errors/timeouts are missing for primary inference, not wrong answers. The two-round maximum is enforced; no further redesign is allowed.
