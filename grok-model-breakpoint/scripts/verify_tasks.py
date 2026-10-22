#!/usr/bin/env python3
"""Confirm each hard task fails while buggy and passes with the reference fix.

Also confirms each easy task fails before any edit. No model calls.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def pytest(workdir: Path, extra_paths):
    cmd = [
        PY, "-m", "pytest", "-q", "--noconftest", "-p", "no:cacheprovider",
        *extra_paths,
    ]
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)[-800:]


def check_hard(task: Path):
    name = task.name
    remove = []
    listing = task / "remove_before_grade.txt"
    if listing.exists():
        remove = [line.strip() for line in listing.read_text().splitlines() if line.strip()]
    with tempfile.TemporaryDirectory(prefix="grok-breakpoint-verify-") as tmp:
        buggy = Path(tmp) / "buggy"
        fixed = Path(tmp) / "fixed"
        shutil.copytree(task / "repo", buggy)
        shutil.copytree(task / "repo", fixed)
        for src in (task / "fixed").iterdir():
            dest = fixed / src.name
            if src.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        for victim in remove:
            target = fixed / victim
            if target.exists():
                target.unlink()
        visible = "tests/test_visible.py"
        hidden = str(task / "hidden" / "test_hidden.py")
        # Hidden tests import the workdir modules. Put the workdir first on PYTHONPATH
        # and run hidden tests from a copied file inside the tree so pytest's rootdir
        # does not become the experiment folder.
        for label, tree in (("buggy", buggy), ("fixed", fixed)):
            grade = tree / "_grade"
            grade.mkdir()
            shutil.copy(task / "hidden" / "test_hidden.py", grade / "test_hidden.py")
        bug_vis, bug_vis_out = pytest(buggy, [visible])
        bug_all, bug_all_out = pytest(buggy, [visible, "_grade/test_hidden.py"])
        ok_all, ok_out = pytest(fixed, [visible, "_grade/test_hidden.py"])
    problems = []
    if bug_vis == 0:
        problems.append(f"visible tests already pass on the buggy repo\n{bug_vis_out}")
    if bug_all == 0:
        problems.append(f"hidden+visible already pass on the buggy repo\n{bug_all_out}")
    if ok_all != 0:
        problems.append(f"reference fix failed\n{ok_out}")
    if problems:
        print(f"FAIL {name}")
        print("\n".join(problems))
        return False
    print(f"ok {name}: buggy visible fails, reference passes")
    return True


def check_easy(task: Path):
    proc = subprocess.run(["node", "test.js"], cwd=task, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"FAIL {task.name}: easy fixture already passes")
        return False
    print(f"ok {task.name}: node test.js fails before the fix")
    return True


def main():
    hard_ok = True
    for task in sorted((ROOT / "tasks" / "hard").iterdir()):
        if task.is_dir():
            hard_ok = check_hard(task) and hard_ok
    easy_ok = True
    for task in sorted((ROOT / "tasks" / "easy").iterdir()):
        if task.is_dir():
            easy_ok = check_easy(task) and easy_ok
    if not (hard_ok and easy_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
