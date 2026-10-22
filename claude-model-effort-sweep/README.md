# Model / effort sweep (Claude Code CLI): cost per solved task

**Question.** Which model and effort setting gives the cheapest solved task on small bug fixes? The sweep covers Haiku 5.5 at low, medium and high effort on 10 tasks, plus Sonnet 5.5 and Opus 5.5.

**Short answer.** All 6 arms solved **10/10**. **Haiku 5.5 cost $0.0035–0.0036 per solved task at every effort level** — about **14× cheaper than Sonnet 5.5** ($0.050) and **30× cheaper than Opus 5.5** ($0.105–0.109), API-equivalent. Effort barely mattered on these tasks: Haiku high wrote 28% more output than low (1,027 vs 804 tokens) but cost the same to the 4th decimal; Opus low vs default differed 4%. Haiku took more turns (4.9–5.6 vs 3.9–4.5) and wrote ~2× the output of Sonnet/Opus, and wall time was a wash (8.6–10.9 s). On tasks this small, the model's price list is the whole story.

## Setup
- Claude Code 2.1.300, Pro sign-in; headless `claude -p "Make \`node test.js\` pass by fixing the code. Do not edit test.js." --output-format stream-json --verbose --dangerously-skip-permissions --strict-mcp-config --no-session-persistence --model <m> [--effort <e>]`, fresh copy of one package per run.
- Arms: `--model haiku --effort low|medium|high` (claude-haiku-5-5), `--model sonnet` (claude-sonnet-5-5, default effort), `--model opus` default and `--effort low` (claude-opus-5-5). `fable` (Fable 5.1) is listed by this build but refused on Pro ("requires usage credits"), so not tested. `xhigh`/`max` efforts skipped for budget.
- 10 tasks: the 10-package bug-fix suite: N01_median, N02_duration, N03_csv, T02_duplicate, T05_stale, T06_neardup, T07_multihunk, T08_insert, T09_delete, T10_replace_all. Pass = `node test.js` exits 0 and test.js unchanged. 1 run per cell, 2 at a time, 2026-10-14 ~19:58–20:03 UTC.
- Est. $ = Claude Code's `total_cost_usd` (list API price). Implied rates (least squares over the runs, $/M input · cache write · cache read · output): Haiku 5.5 0.10 · 0.20 · 0.01 · 0.50; Sonnet 5.5 2 · 4 · 0.10 · 10; Opus 5.5 4 · 8 · 0.20 · 20. **API-equivalent estimates only; Pro isn't billed per token**, and Pro's usage window weights models differently from these prices.

## Exact commands
```bash
scripts/harness/driver_cc.sh scripts/jobs.txt 2 results/driver.log
python scripts/analyze.py
```

## Results (10 tasks per arm)
| Arm | Solved | Est. $ total | **$ per solved** | Tokens/task | Output/task | Model calls | Tool calls | Wall |
|---|---|---|---|---|---|---|---|---|
| haiku low | 10/10 | $0.036 | **$0.0036** | 77,788 | 804 | 5.4 | 4.4 | 10.9 s |
| haiku medium | 10/10 | $0.035 | **$0.0035** | 73,486 | 880 | 4.9 | 3.9 | 9.4 s |
| haiku high | 10/10 | $0.037 | **$0.0036** | 81,196 | 1,027 | 5.6 | 4.6 | 9.8 s |
| sonnet default | 10/10 | $0.504 | **$0.050** | 71,771 | 486 | 4.5 | 3.5 | 10.3 s |
| opus low | 10/10 | $1.047 | **$0.105** | 69,886 | 493 | 3.9 | 2.9 | 8.6 s |
| opus default | 10/10 | $1.093 | **$0.109** | 73,904 | 549 | 4.2 | 3.2 | 10.2 s |

`results/summary.csv`, `results/runs.csv`, raw stream-json in `results/raw/`. Chart: `results/chart.png`.

## Caveats
- The tasks are too easy to separate the models on quality: everything passed. Cost per solved task will diverge once the cheap model starts failing; this only shows Haiku is enough for small, well-specified fixes.
- 1 run per cell (Claude's run-to-run variance ~1%, from my [agent cost variance study](https://github.com/nankris/agent-cost-variance)).
- Prices are what Claude Code 2.1.300 reports for these models; the Haiku figures look very low but they're the CLI's own numbers.
