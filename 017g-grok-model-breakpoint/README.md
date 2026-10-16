# 017g — Where the cheaper Grok model breaks

Rerun of experiment 017. The original run (Haiku vs Opus on 10 easy JavaScript bugs) was a 100% ceiling, so it could not show where the cheap model fails. This folder does not modify `017-claude-model-effort-sweep/`.

## Hypothesis

On the 10 hard tasks, **grok-4.5** (cheap arm) has a pass rate at least 20 percentage points lower than **grok-4.7** (strong arm).

Pass rate is the share of scored trials. One trial is one fresh repository copy of one task, one model, one rep. Round 1 has 10 hard tasks × 2 reps = 20 trials per arm.

## Decision rule

Written before any scored Grok run. The test is one-sided Fisher's exact test on pass counts, plus a Newcombe hybrid-score 95% interval for the gap so a tie can be distinguished from "too little data."

Let the hard-task table be

| | pass | fail |
|---|---|---|
| cheap (grok-4.5) | a | n_c − a |
| strong (grok-4.7) | b | n_s − b |

- **Gap** Δ = b/n_s − a/n_c.
- **Fisher.** `scipy.stats.fisher_exact` on `[[a, n_c−a], [b, n_s−b]]` with `alternative="less"` (cheap pass odds lower than strong).
- **Interval.** Newcombe hybrid-score 95% CI for Δ, using Wilson intervals for each rate (z = 1.959963984540054).

Apply the first matching row:

1. **STILL INCONCLUSIVE** if either arm has more than 4 excluded hard trials (infrastructure failures after retries). A quota outage is not a model failure.
2. **PROVEN** if Fisher p < 0.05 and Δ ≥ 0.20.
3. **DISPROVEN** if the Newcombe upper bound is < 0.20. That includes a tie, a ceiling, a floor, and any gap reliably smaller than 20 points. The cheap arm being better also lands here, because the claim is a ≥20 point deficit.
4. **STILL INCONCLUSIVE** otherwise. The usual case is a gap that is large in the sample but with p ≥ 0.05, or a small gap whose upper bound still reaches 0.20.

The rule is applied only to a finished round: every planned hard trial was either scored or excluded. An unfinished round is STILL INCONCLUSIVE.

Self-check, computed before the run and locked in `scripts/decision.py`: both 20/20 → DISPROVEN (upper 0.161); both 19/20 → DISPROVEN (upper 0.191); both 18/20 → INCONCLUSIVE (upper 0.214); strong 20 vs cheap 16 → INCONCLUSIVE (p = 0.053); strong 20 vs cheap 15 → PROVEN (p = 0.024, Δ = 0.25).

Easy tasks are a control from experiment 017. They are not in the Fisher table.

### Round 2, only if round 1 is STILL INCONCLUSIVE

One redesign, pre-registered, no peeking at which items to rewrite: add reps 3 and 4 on the same 10 hard tasks, same prompts, models, grader, and timeouts. Pool every scored hard trial from both rounds (40 per arm if nothing is excluded) and apply the same rule once. Do not edit specs or tests between rounds. Stop after that second look even if it is still inconclusive. Easy tasks are not repeated.

Trials are two reps of the same task, so they are not independent. Fisher treats them as independent, which is what this rule specifies. A task-level McNemar check (a task passes only when both reps pass) is reported and does not change the verdict.

## Arms

`grok models` on grok 1.0.52, 2026-10-15, before any scored run:

| Model id | Catalog text | Role |
|---|---|---|
| grok-4.7 | default, "SpaceXAI's latest frontier model" | **strong** |
| grok-4.7-build-fast | "Fast variant. 2x the price." | not used |
| grok-4.6 | no description | not used |
| grok-4.5 | no description, oldest id | **cheap** |

There is no Haiku-style discount in this catalog. Published xAI list prices for grok-4.5, grok-4.6, and grok-4.7 are the same $2 / $6 per million input/output tokens under 200k, with grok-4.5's cached input slightly cheaper ($0.30 vs $0.50). The only model described as fast is grok-4.7-build-fast, and the catalog prices it at 2×, so it is not the cheap arm. The cheap arm is the oldest listed model, grok-4.5. The strong arm is the frontier default, grok-4.7.

Both arms use `--reasoning-effort high` (the catalog default for both) so effort is not a second factor. CLI `total_cost_usd` is an API-equivalent estimate on SuperGrok, not a measured bill.

## Tasks

- **10 hard tasks** (original, multi-file). The agent sees `SPEC.md` and one visible pytest. The grader restores `tests/`, copies hidden pytest in only after the agent exits, and runs both. `--sandbox strict` keeps the agent from reading the hidden files (read is limited to the cwd, system paths, and `~/.grok`).
- **5 easy tasks** copied from 017's suite, unchanged: `N01_median`, `N02_duration`, `N03_csv`, `T02_duplicate`, `T07_multihunk`. `T05_stale` was not copied: its fixture already passes (`return v + 0`).

A hard trial passes only when visible and hidden pytest both exit 0. An easy trial passes when `node test.js` exits 0 after `test.js` and `data.csv` are restored, so the fix has to live in `broken.js`.

Same wall clock and `--max-turns 30` for both models. Hitting that budget and still failing tests is a fail. A 429, usage-limit, sandbox startup error, or model-id mismatch is infrastructure: retry twice, then exclude the trial.

## Command

```bash
grok --no-auto-update -p "<prompt>" --always-approve --cwd <fresh copy> \
  --output-format json --model <grok-4.5|grok-4.7> --reasoning-effort high \
  --disable-web-search --no-subagents --no-plan --max-turns 30 \
  --sandbox strict --no-alt-screen
```

One unscored smoke call checks that `--sandbox strict` starts. It is not a task and is not in the Fisher table. If strict refuses to start, scored runs drop only that flag and the writeup says so. That decision is made before any scored trial.

**Smoke result (before any scored trial).** Strict refused to start: `symlinked GROK_HOME is not allowed under sandbox write-deny: /home/sandbox/.grok`. Scored runs omit `--sandbox`. See `results/sandbox_smoke.txt`. Hidden tests are still absent from the agent directory. The prompt forbids searching outside it.

**Model id check (before any graded trial).** The first calls returned `modelUsage` key `grok-4.5-build` for `--model grok-4.5`, with a normal `end_turn` and a cost. Those workdirs were discarded ungraded. A trial matches the requested arm when every reported id is exactly the requested id or that id plus `-build`. `grok-4.7-build-fast` does not match `grok-4.7`.

Round 1 order is shuffled with seed 17. Two or three runs at a time. Each trial is a new directory under `/tmp/017g-work`, never inside this folder, so the copy the agent sees does not contain `hidden/` or `fixed/`.

## Compute

CLI experiment. No Colab GPU session is started. Other sessions already occupied the account's two GPU slots and were not touched.

- Before, 2026-10-15T07:03:01Z: balance **177.71** CU, usage rate 3.08/hr, active assignments 2 (not this experiment).
- GPU for this experiment: **none**.
- CU used by this experiment: **0** (updated again after the run; the shared balance can move because other sessions are live).

## How to reproduce

```bash
python3 scripts/materialize_tasks.py
python3 scripts/verify_tasks.py
python3 scripts/decision.py
python3 scripts/run_round.py --round 1
/workspace/tools/mlenv/bin/python scripts/analyze.py
```
