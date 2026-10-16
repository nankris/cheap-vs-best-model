#!/usr/bin/env python3
"""Pre-registered decision rule for 017g. No Grok calls."""
import math

Z = 1.959963984540054


def wilson(k, n, z=Z):
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, center - margin), min(1.0, center + margin))


def newcombe(k_strong, n_strong, k_cheap, n_cheap, z=Z):
    """95% CI for p_strong - p_cheap (Newcombe hybrid score)."""
    p1 = k_strong / n_strong
    p2 = k_cheap / n_cheap
    l1, u1 = wilson(k_strong, n_strong, z)
    l2, u2 = wilson(k_cheap, n_cheap, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


def fisher_less(k_strong, n_strong, k_cheap, n_cheap):
    """One-sided Fisher p: cheap pass rate lower than strong."""
    from scipy.stats import fisher_exact

    table = [
        [k_cheap, n_cheap - k_cheap],
        [k_strong, n_strong - k_strong],
    ]
    _, p = fisher_exact(table, alternative="less")
    return float(p)


def decide(k_strong, n_strong, k_cheap, n_cheap, excluded_strong=0, excluded_cheap=0):
    """Return a dict with verdict, gap, CI, and Fisher p.

    Rule (README): too many exclusions → STILL INCONCLUSIVE;
    else PROVEN if p<0.05 and gap>=0.20;
    else DISPROVEN if Newcombe upper < 0.20;
    else STILL INCONCLUSIVE.
    """
    if excluded_strong > 4 or excluded_cheap > 4 or n_strong <= 0 or n_cheap <= 0:
        return {
            "verdict": "STILL INCONCLUSIVE",
            "reason": "excluded>4 or empty arm",
            "delta": None,
            "ci_low": None,
            "ci_high": None,
            "p": None,
            "k_strong": k_strong,
            "n_strong": n_strong,
            "k_cheap": k_cheap,
            "n_cheap": n_cheap,
        }
    delta, lo, hi = newcombe(k_strong, n_strong, k_cheap, n_cheap)
    p = fisher_less(k_strong, n_strong, k_cheap, n_cheap)
    if p < 0.05 and delta >= 0.20 - 1e-12:
        verdict = "PROVEN"
        reason = "fisher p<0.05 and gap>=0.20"
    elif hi < 0.20:
        verdict = "DISPROVEN"
        reason = "Newcombe upper bound < 0.20"
    else:
        verdict = "STILL INCONCLUSIVE"
        reason = "gap not established and not ruled out"
    return {
        "verdict": verdict,
        "reason": reason,
        "delta": delta,
        "ci_low": lo,
        "ci_high": hi,
        "p": p,
        "k_strong": k_strong,
        "n_strong": n_strong,
        "k_cheap": k_cheap,
        "n_cheap": n_cheap,
    }


def _selftest():
    cases = [
        (20, 20, 20, 20, "DISPROVEN"),
        (19, 20, 19, 20, "DISPROVEN"),
        (18, 20, 18, 20, "STILL INCONCLUSIVE"),
        (20, 20, 16, 20, "STILL INCONCLUSIVE"),
        (20, 20, 15, 20, "PROVEN"),
        (0, 20, 0, 20, "DISPROVEN"),
        (40, 40, 32, 40, "PROVEN"),
        (36, 40, 36, 40, "DISPROVEN"),
        (20, 20, 20, 20, "STILL INCONCLUSIVE", 5, 0),
    ]
    bad = []
    for row in cases:
        if len(row) == 5:
            ks, ns, kc, nc, expect = row
            ex_s = ex_c = 0
        else:
            ks, ns, kc, nc, expect, ex_s, ex_c = row
        got = decide(ks, ns, kc, nc, ex_s, ex_c)
        if got["verdict"] != expect:
            bad.append((row, got))
    if bad:
        raise SystemExit(f"decision self-test failed: {bad}")
    print("decision self-test ok")
    for ks, ns, kc, nc, expect in [
        (20, 20, 20, 20, "DISPROVEN"),
        (19, 20, 19, 20, "DISPROVEN"),
        (18, 20, 18, 20, "STILL INCONCLUSIVE"),
        (20, 20, 16, 20, "STILL INCONCLUSIVE"),
        (20, 20, 15, 20, "PROVEN"),
    ]:
        g = decide(ks, ns, kc, nc)
        print(
            f"  strong {ks}/{ns} cheap {kc}/{nc}: {g['verdict']} "
            f"d={g['delta']:.3f} CI[{g['ci_low']:.3f},{g['ci_high']:.3f}] p={g['p']:.4f}"
        )


if __name__ == "__main__":
    _selftest()
