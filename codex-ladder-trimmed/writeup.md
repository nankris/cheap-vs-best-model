# Trimmed Codex difficulty ladder

**Verdict: STILL INCONCLUSIVE.** Tier 4 is primary: gpt-6-astra/high minus gpt-6-luna/low. 4/48 evaluable fresh trials completed, 0 infrastructure attempts. Elapsed wall time at analysis: 1.4 minutes. GPU: none; CU used: **0**.

| Tier | Paired tasks | Luna / low | Astra / high | Gap (points) | Paired 95% CI (points) |
|---|---:|---:|---:|---:|---:|


Each task has one fresh call per arm. Paired task percentile bootstrap: 100,000 resamples, seed 1703. Exact one-sided task sign p=unavailable. The primary rule requires positive lower CI plus sign p<.05 for superiority; reverse superiority or an entire CI inside ±10 points disproves the hypothesis. Constant-zero outcomes use the inherited exact discordance bound; constant-nonzero outcomes use the inherited Hoeffding guard. See results/summary.json for unguarded bootstrap intervals, guard, and discordance counts.

The fixed sample is 12 tasks per tier. The previous round had only five tier-3 tasks: seven additional batch tasks reuse its first seven top-tier algorithms and unchanged batch template. Tier 4 retains its first 12 tasks in original order; no historical outcomes are pooled. All 24 references pass and all 24 deliberately broken starters fail. Filesystem isolation probe denies hidden suite access and unmounting its cover. Source snapshots are graded after each call, using the unchanged inherited grader, algorithm oracles, repeated calls and Result contract checks. Results and raw events checkpoint directly to local disk on every completion; retries preserve infrastructure logs and do not convert service failures into model failures.

The fixed sample cannot guarantee a conclusive verdict under the fixed rule. In particular, zero tier-4 discordances at n=12 give an exact upper bound of 22.09%, exceeding the 10-point margin; at least 29 tasks would be required. A zero-width raw bootstrap at a ceiling is not evidence of equivalence. If neither rule holds, STILL INCONCLUSIVE means the fixed sampling budget is exhausted; the reported elapsed time distinguishes this from wall-time exhaustion. No post-hoc margin changes or extra tasks were used. Planning assumptions and power are in results/power.json.

These are purposive synthetic Python algorithms sharing journal machinery, so exchangeable-task bootstrap assumptions limit population generalization. Algorithms overlap across tiers; tier 3 is descriptive only. The contrast bundles model and effort. One repetition cannot characterize within-task generation variance. No production-wide ranking or difficulty breakpoint is established by these two tiers.

Reproduce with scripts/validate.py, scripts/run.py (resumable, four workers), and scripts/analyze.py. private/suite.json is the frozen selected suite; inherited build.py is only a fixture/helper library and should not regenerate the untrimmed suite. Raw per-call events, stderr, invocation, metadata, source snapshots and grading are under results/T*/; results/trials.csv is the analysis table. Default Codex account only. The [original study](../codex-model-breakpoint/) and the previous round's folders were read only. No GPU or network data was needed.
