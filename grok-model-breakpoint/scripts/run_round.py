#!/usr/bin/env python3
"""Run one round of the Grok model-breakpoint study. Fresh repo copy per trial. Resumable.

Round 1: 10 hard + 5 easy, 2 reps, both models.
Round 2: 10 hard only, reps 3 and 4, both models. Run only after round 1 is inconclusive.
"""
import argparse
import csv
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks"
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"
WORK = Path("/tmp/grok-breakpoint-work")
CSV_PATH = RESULTS / "runs.csv"
SITE = Path(os.environ.get("GROK_RUN_SITE_PACKAGES", "/home/sandbox/.local/lib/python3.12/site-packages"))
PY = sys.executable
ARMS = [("cheap", "grok-4.5"), ("strong", "grok-4.7")]
EASY = ["N01_median", "N02_duration", "N03_csv", "T02_duplicate", "T07_multihunk"]
HARD_TIMEOUT = 720
EASY_TIMEOUT = 300
MAX_TURNS = 30
FIELDS = [
    "ts", "round", "role", "model", "task", "difficulty", "rep", "attempt",
    "status", "passed", "fisher_include", "cost_usd", "cost_ticks",
    "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
    "output_tokens", "reasoning_tokens", "num_turns", "stop_reason",
    "models_reported", "latency_s", "exit_code", "sandbox", "error",
]

# Do not match a bare "429": token counts such as 29429 contain those digits.
LIMIT_MARKERS = (
    "rate limit", "usage limit", "too many requests", "http 429",
    "status 429", "error 429", "limit reached", "exceeded your",
    "quota exceeded", "usage quota",
)

_csv_lock = __import__("threading").Lock()
_stop = __import__("threading").Event()


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "driver.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sandbox_flag():
    path = RESULTS / "sandbox_mode.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "strict"


def load_done():
    done = set()
    if not CSV_PATH.exists():
        return done
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status") in {"pass", "fail"}:
                done.add((row["round"], row["role"], row["task"], row["rep"]))
    return done


def append_row(row):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with _csv_lock:
        new = not CSV_PATH.exists()
        with CSV_PATH.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            if new:
                writer.writeheader()
            writer.writerow({key: row.get(key, "") for key in FIELDS})
            fh.flush()


def parse_grok_json(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and any(k in obj for k in ("stopReason", "usage", "modelUsage")):
            found = obj
    return found


def copy_vendor(dest: Path):
    vendor = dest / "_vendor"
    if vendor.exists():
        shutil.rmtree(vendor)
    vendor.mkdir(parents=True)
    for name in ("pytest", "_pytest", "pluggy", "iniconfig", "packaging"):
        shutil.copytree(
            SITE / name,
            vendor / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def prepare_workdir(difficulty, task, key):
    src = TASKS / difficulty / task
    if difficulty == "hard":
        src = src / "repo"
    dest = WORK / key
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    if difficulty == "hard":
        copy_vendor(dest)
    return dest


def restore_easy(task, work):
    pristine = TASKS / "easy" / task
    for path in pristine.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(pristine)
        if rel.as_posix() == "broken.js":
            continue
        target = work / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def restore_hard(task, work):
    pristine = TASKS / "hard" / task / "repo"
    tests = work / "tests"
    if tests.exists():
        shutil.rmtree(tests)
    shutil.copytree(pristine / "tests", tests)
    for name in ("conftest.py", "pytest.ini", "setup.cfg", "pyproject.toml", "tox.ini"):
        candidate = work / name
        if candidate.exists() and not (pristine / name).exists():
            candidate.unlink()
    listing = TASKS / "hard" / task / "remove_before_grade.txt"
    if listing.exists():
        for rel in listing.read_text(encoding="utf-8").splitlines():
            rel = rel.strip()
            if not rel:
                continue
            target = work / rel
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
    grade = work / "_grade"
    if grade.exists():
        shutil.rmtree(grade)
    grade.mkdir()
    shutil.copy(TASKS / "hard" / task / "hidden" / "test_hidden.py", grade / "test_hidden.py")


def grade(difficulty, task, work):
    if difficulty == "easy":
        restore_easy(task, work)
        proc = subprocess.run(
            ["node", "test.js"], cwd=work, capture_output=True, text=True, timeout=120,
        )
        tail = (proc.stdout + "\n" + proc.stderr)[-500:].replace("\n", " ")
        return proc.returncode == 0, tail
    restore_hard(task, work)
    proc = subprocess.run(
        [PY, "-m", "pytest", "-q", "--noconftest", "-p", "no:cacheprovider",
         "tests/test_visible.py", "_grade/test_hidden.py"],
        cwd=work, capture_output=True, text=True, timeout=180,
    )
    tail = (proc.stdout + "\n" + proc.stderr)[-500:].replace("\n", " ")
    return proc.returncode == 0, tail


def looks_limited(text):
    low = (text or "").lower()
    return any(marker in low for marker in LIMIT_MARKERS)


def model_matches(requested, reported):
    """CLI --model grok-4.5 is billed as grok-4.5-build. Do not accept the 2x fast SKU."""
    if not reported:
        return True
    allowed = {requested, requested + "-build"}
    return all(name in allowed for name in reported)


def run_grok(prompt, work, model, timeout, sandbox):
    cmd = [
        "grok", "--no-auto-update", "-p", prompt,
        "--always-approve", "--cwd", str(work),
        "--output-format", "json",
        "--model", model,
        "--reasoning-effort", "high",
        "--disable-web-search", "--no-subagents", "--no-plan",
        "--max-turns", str(MAX_TURNS),
        "--no-alt-screen",
    ]
    if sandbox and sandbox != "off":
        cmd.extend(["--sandbox", sandbox])
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    started = time.time()
    proc = subprocess.Popen(
        cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True, env=env,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, err = proc.communicate(timeout=10)
        code = -9
        err = (err or "") + "\nTIMEOUT"
    return code, out or "", err or "", time.time() - started, cmd


def one_trial(job, sandbox):
    if _stop.is_set():
        return None
    round_no, role, model, task, difficulty, rep = job
    key = f"r{round_no}_{role}_{task}_r{rep}"
    prompt = (ROOT / "scripts" / f"prompt_{difficulty}.txt").read_text(encoding="utf-8").strip()
    timeout = HARD_TIMEOUT if difficulty == "hard" else EASY_TIMEOUT
    last = None
    for attempt in (1, 2, 3):
        if _stop.is_set():
            return last
        work = prepare_workdir(difficulty, task, f"{key}_a{attempt}")
        log(f"start {key} attempt {attempt} model={model} sandbox={sandbox}")
        code, out, err, latency, cmd = run_grok(prompt, work, model, timeout, sandbox)
        raw_base = RAW / key
        RAW.mkdir(parents=True, exist_ok=True)
        (raw_base.with_suffix(".stdout.json")).write_text(out, encoding="utf-8")
        (raw_base.with_suffix(".stderr.txt")).write_text(err[-8000:], encoding="utf-8")
        (raw_base.with_suffix(".cmd.txt")).write_text(" ".join(cmd[:6]) + " ...", encoding="utf-8")
        data = parse_grok_json(out)
        blob = (out + "\n" + err)[-4000:]
        usage = (data or {}).get("usage") or {}
        reported = list(((data or {}).get("modelUsage") or {}).keys())
        stop_reason = (data or {}).get("stopReason", "")
        limited = looks_limited(blob)
        mismatch = not model_matches(model, reported)
        started_ok = data is not None and (stop_reason or reported or usage)
        infra = limited or mismatch or not started_ok or code not in (0, None)
        # A timeout that still produced a transcript with turns is a real attempt.
        turns = (data or {}).get("num_turns") or 0
        if code == -9 and started_ok and turns:
            infra = False
        if code not in (0, -9) and started_ok and not limited and not mismatch:
            infra = False
        status = "infra"
        passed = ""
        include = 0
        tail = ""
        if not infra:
            try:
                ok, tail = grade(difficulty, task, work)
            except subprocess.TimeoutExpired:
                ok, tail = False, "GRADE TIMEOUT"
            status = "pass" if ok else "fail"
            passed = int(ok)
            include = 1 if difficulty == "hard" else 0
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "round": round_no,
            "role": role,
            "model": model,
            "task": task,
            "difficulty": difficulty,
            "rep": rep,
            "attempt": attempt,
            "status": status,
            "passed": passed,
            "fisher_include": include,
            "cost_usd": (data or {}).get("total_cost_usd", ""),
            "cost_ticks": (data or {}).get("total_cost_usd_ticks", ""),
            "input_tokens": usage.get("input_tokens", ""),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", ""),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", ""),
            "output_tokens": usage.get("output_tokens", ""),
            "reasoning_tokens": usage.get("reasoning_tokens", ""),
            "num_turns": (data or {}).get("num_turns", ""),
            "stop_reason": stop_reason,
            "models_reported": ",".join(reported),
            "latency_s": f"{latency:.1f}",
            "exit_code": code,
            "sandbox": sandbox,
            "error": (tail if not infra else blob[-400:].replace("\n", " "))[:400],
        }
        append_row(row)
        last = row
        log(f"done {key} attempt {attempt} status={status} cost={row['cost_usd']} turns={row['num_turns']} {latency:.0f}s")
        shutil.rmtree(work, ignore_errors=True)
        if status != "infra":
            return row
        if limited:
            log(f"limit marker on {key}; backing off")
            _stop.set()
            (RESULTS / "QUOTA_STOP").write_text(blob[-500:], encoding="utf-8")
            return row
        time.sleep(20 * attempt)
    return last


def jobs_for(round_no, done):
    reps = (1, 2) if round_no == 1 else (3, 4)
    tasks = [(name, "hard") for name in sorted(p.name for p in (TASKS / "hard").iterdir() if p.is_dir())]
    if round_no == 1:
        tasks += [(name, "easy") for name in EASY]
    jobs = []
    for role, model in ARMS:
        for task, difficulty in tasks:
            for rep in reps:
                key = (str(round_no), role, task, str(rep))
                if key in done:
                    continue
                jobs.append((str(round_no), role, model, task, difficulty, str(rep)))
    random.Random(17 + round_no).shuffle(jobs)
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()
    if (RESULTS / "QUOTA_STOP").exists():
        log("QUOTA_STOP present; not starting")
        sys.exit(2)
    WORK.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    sandbox = sandbox_flag()
    done = load_done()
    jobs = jobs_for(args.round, done)
    log(f"round {args.round}: {len(jobs)} trials, workers={args.jobs}, sandbox={sandbox}")
    if not jobs:
        log("nothing to run")
        return
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = []
        for job in jobs:
            if _stop.is_set():
                break
            futures.append(pool.submit(one_trial, job, sandbox))
            time.sleep(1.5)
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                log(f"worker crashed: {exc}")
            if _stop.is_set():
                break
    log("round driver returned")


if __name__ == "__main__":
    main()
