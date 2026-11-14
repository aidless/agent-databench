#!/usr/bin/env python3
"""Offline pipeline benchmark for agent-databench.

Runs the real test suite and the real --fake plumbing replay, and checks the
committed replay result. Does NOT consult a model or network.

This is the honest claim the harness can make: the plumbing (loop/sandbox/scoring/
report) is verified end-to-end on 20 standard-answer tasks, with `llm: fake`
marking every row so no capability claim leaks in.

Usage: python benchmarks/bench_pipeline.py
Exit: 0 only if tests pass AND 20/20 replay passes, else 1.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "results" / "base-fake.jsonl"


def main():
    print("=== agent-databench pipeline verification ===")
    all_ok = True

    # 1. Test suite
    r = subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"],
                       capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    print(out)
    passed_line = [l for l in out.splitlines() if "passed" in l and "failed" not in l]
    ok = r.returncode == 0 and any("7 passed" in l for l in passed_line)
    print(f"  [{'PASS' if ok else 'FAIL'}] test suite (expect 7 passed)")
    all_ok &= ok

    # 2. Committed replay result
    if REPLAY.exists():
        rows = [json.loads(l) for l in REPLAY.read_text().splitlines() if l.strip()]
        n = len(rows)
        passed = sum(1 for x in rows if x.get("passed"))
        distinct = len(set(x.get("task_id") for x in rows))
        all_fake = all(x.get("llm") == "fake" for x in rows)
        ok = n == 20 and passed == 20 and distinct == 20 and all_fake
        print(f"  [{'PASS' if ok else 'FAIL'}] committed replay "
              f"(rows={n}, passed={passed}, distinct={distinct}, all_fake={all_fake})")
        all_ok &= ok
    else:
        print("  [FAIL] results/base-fake.jsonl not found")
        all_ok = False

    print(f"RESULT: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
