#!/usr/bin/env python3
"""Score 017g from results/runs.csv and write the chart. No model calls."""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from decision import decide, wilson  # noqa: E402

RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "runs.csv"


def last_rows():
    grouped = {}
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (row["round"], row["role"], row["task"], row["rep"])
            grouped[key] = row
    return list(grouped.values())


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def planned(round_no, difficulty):
    hard = sorted(p.name for p in (ROOT / "tasks" / "hard").iterdir() if p.is_dir())
    easy = ["N01_median", "N02_duration", "N03_csv", "T02_duplicate", "T07_multihunk"]
    tasks = hard if difficulty == "hard" else easy
    reps = (1, 2) if round_no == 1 else (3, 4)
    return {(role, task, str(rep)) for role in ("cheap", "strong") for task in tasks for rep in reps}


def arm_stats(rows):
    out = {}
    for role in ("cheap", "strong"):
        subset = [r for r in rows if r["role"] == role and r["status"] in {"pass", "fail"}]
        passed = sum(r["status"] == "pass" for r in subset)
        n = len(subset)
        costs = [num(r["cost_usd"]) for r in subset]
        costs = [c for c in costs if c is not None]
        lo, hi = wilson(passed, n) if n else (None, None)
        out[role] = {
            "passed": passed,
            "n": n,
            "rate": (passed / n) if n else None,
            "wilson": [lo, hi],
            "mean_cost": (sum(costs) / len(costs)) if costs else None,
            "total_cost": sum(costs) if costs else None,
            "mean_turns": _mean(subset, "num_turns"),
            "mean_latency": _mean(subset, "latency_s"),
            "mean_output": _mean(subset, "output_tokens"),
        }
    return out


def _mean(rows, field):
    vals = [num(r[field]) for r in rows]
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def mcnemar(rows):
    """Task passes only when every scored rep for that task passed. Report only."""
    by = defaultdict(dict)
    for row in rows:
        if row["status"] not in {"pass", "fail"}:
            continue
        by[(row["role"], row["task"])][row["rep"]] = row["status"] == "pass"
    tasks = sorted({task for (_, task) in by})
    both = cheap_only = strong_only = neither = 0
    used = 0
    for task in tasks:
        if ("cheap", task) not in by or ("strong", task) not in by:
            continue
        c_reps = by[("cheap", task)]
        s_reps = by[("strong", task)]
        if not c_reps or not s_reps:
            continue
        c_ok = all(c_reps.values())
        s_ok = all(s_reps.values())
        used += 1
        if c_ok and s_ok:
            both += 1
        elif c_ok and not s_ok:
            cheap_only += 1
        elif s_ok and not c_ok:
            strong_only += 1
        else:
            neither += 1
    # Exact McNemar: discordant pairs, two-sided binomial.
    disc = cheap_only + strong_only
    if disc == 0:
        p = 1.0
    else:
        # P(X>=max) * 2 under Bin(disc, 0.5), capped at 1. strong_only is b>c.
        k = min(cheap_only, strong_only)
        # two-sided exact
        from math import comb
        tail = sum(comb(disc, i) for i in range(0, k + 1)) / (2 ** disc)
        p = min(1.0, 2 * tail)
    return {
        "tasks": used,
        "both_pass": both,
        "cheap_only": cheap_only,
        "strong_only": strong_only,
        "neither": neither,
        "p_two_sided": p,
    }


def chart(summary, verdict):
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4))
    colors = {"cheap": "#d55e00", "strong": "#0072b2"}
    labels = {"cheap": "grok-4.5 cheap", "strong": "grok-4.7 strong"}
    for ax, difficulty, title in (
        (axes[0], "hard", "Hard tasks"),
        (axes[1], "easy", "Easy tasks (017 control)"),
    ):
        stats = summary[difficulty]
        xs = [0, 1]
        roles = ["cheap", "strong"]
        rates, yerr_lo, yerr_hi, ns = [], [], [], []
        for role in roles:
            st = stats[role]
            rate = 0 if st["rate"] is None else st["rate"] * 100
            rates.append(rate)
            if st["wilson"][0] is None:
                yerr_lo.append(0)
                yerr_hi.append(0)
            else:
                lo = st["wilson"][0] * 100
                hi = st["wilson"][1] * 100
                yerr_lo.append(rate - lo)
                yerr_hi.append(hi - rate)
            ns.append(st["n"])
        bars = ax.bar(
            xs, rates, color=[colors[r] for r in roles], width=0.72,
            yerr=[yerr_lo, yerr_hi], capsize=4, ecolor="#222222",
        )
        ax.set_xticks(xs, [labels[r] for r in roles])
        ax.set_ylim(0, 100)
        ax.set_ylabel("Pass rate (%)")
        ax.set_title(title)
        for bar, role, n in zip(bars, roles, ns):
            st = stats[role]
            passed = st["passed"]
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                min(96, bar.get_height() + 3),
                f"{passed}/{n}",
                ha="center", va="bottom", fontsize=9,
            )
        ax.axhline(95, color="#888888", ls="--", lw=0.7)
    fig.suptitle(f"017g cheap vs strong  ·  {verdict}", fontsize=12)
    fig.text(
        0.5, 0.01,
        "Wilson 95% CI. Dashed line is 95%. Hard-task verdict uses Fisher's exact test, not these bars.",
        ha="center", fontsize=8, color="#333333",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    for path in (ROOT / "chart.png", RESULTS / "chart.png"):
        fig.savefig(path, dpi=140)
    plt.close(fig)


def main():
    rows = last_rows()
    rounds_present = sorted({int(r["round"]) for r in rows})
    # Pool hard trials from every finished round that was planned.
    hard_rows = [r for r in rows if r["difficulty"] == "hard"]
    easy_rows = [r for r in rows if r["difficulty"] == "easy" and r["round"] == "1"]
    # Completion: round 1 hard must be complete. If round 2 rows exist, its hard trials too.
    missing = []
    for round_no in (1, 2):
        have = {
            (r["role"], r["task"], r["rep"])
            for r in hard_rows
            if r["round"] == str(round_no) and r["status"] in {"pass", "fail", "infra"}
        }
        # A key with only infra still counts as attempted.
        if round_no == 2 and not any(r["round"] == "2" for r in rows):
            continue
        need = planned(round_no, "hard")
        # planned keys are (role, task, rep); have matches.
        gap = sorted(need - have)
        if gap:
            missing.append({"round": round_no, "missing": len(gap), "examples": gap[:8]})
    excluded = {
        role: sum(1 for r in hard_rows if r["role"] == role and r["status"] == "infra")
        for role in ("cheap", "strong")
    }
    scored = [r for r in hard_rows if r["status"] in {"pass", "fail"}]
    stats_hard = arm_stats(scored)
    stats_easy = arm_stats([r for r in easy_rows if r["status"] in {"pass", "fail"}])
    finished = not missing
    if not finished:
        verdict = {
            "verdict": "STILL INCONCLUSIVE",
            "reason": "round unfinished",
            "delta": None, "ci_low": None, "ci_high": None, "p": None,
            "k_strong": stats_hard["strong"]["passed"],
            "n_strong": stats_hard["strong"]["n"],
            "k_cheap": stats_hard["cheap"]["passed"],
            "n_cheap": stats_hard["cheap"]["n"],
        }
    else:
        verdict = decide(
            stats_hard["strong"]["passed"], stats_hard["strong"]["n"],
            stats_hard["cheap"]["passed"], stats_hard["cheap"]["n"],
            excluded["strong"], excluded["cheap"],
        )
    summary = {
        "verdict": verdict,
        "excluded_hard": excluded,
        "missing": missing,
        "rounds": rounds_present,
        "hard": stats_hard,
        "easy": stats_easy,
        "mcnemar_task_level": mcnemar(scored),
        "n_rows_last": len(rows),
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["difficulty", "role", "passed", "n", "rate", "wilson_low", "wilson_high",
                         "mean_cost_usd", "total_cost_usd", "mean_turns", "mean_latency_s"])
        for difficulty, stats in (("hard", stats_hard), ("easy", stats_easy)):
            for role, st in stats.items():
                writer.writerow([
                    difficulty, role, st["passed"], st["n"], st["rate"],
                    None if st["wilson"][0] is None else st["wilson"][0],
                    None if st["wilson"][1] is None else st["wilson"][1],
                    st["mean_cost"], st["total_cost"], st["mean_turns"], st["mean_latency"],
                ])
    chart({"hard": stats_hard, "easy": stats_easy}, verdict["verdict"])
    print(json.dumps(verdict, indent=2))
    print("chart written")


if __name__ == "__main__":
    main()
