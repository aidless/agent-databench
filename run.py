#!/usr/bin/env python3
"""Run the benchmark.

  python3 run.py --config configs/base.yaml            # real LLM (needs .env)
  python3 run.py --config configs/base.yaml --fake     # plumbing check, offline
  python3 run.py ... --limit 3                         # quick subset

Fake mode replays scripted answers: it validates wiring (loop, sandbox,
scoring, reporting) and says NOTHING about model capability. Results carry
the llm name so a fake row can never masquerade as a real one.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agent_databench.loop import run_episode  # noqa: E402
from agent_databench.scoring import score_answer  # noqa: E402
from agent_databench.llm import make_llm  # noqa: E402


def load_env(path=ROOT / ".env"):
    if path.exists():
        for line in path.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--tasks", default=str(ROOT / "tasks" / "tasks.jsonl"))
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default=None, help="results jsonl path")
    args = ap.parse_args()

    load_env()
    cfg = yaml.safe_load(Path(args.config).read_text())
    tasks = [json.loads(l) for l in Path(args.tasks).read_text().splitlines() if l.strip()]
    if args.limit:
        tasks = tasks[: args.limit]

    real_llm = None if args.fake else make_llm(False, {})
    rows = []
    for task in tasks:
        llm = make_llm(True, task) if args.fake else real_llm
        before = llm.usage
        episode = run_episode(task, llm, cfg)
        ok = score_answer(task, episode["answer"])
        after = llm.usage
        usage = {k: after[k] - before[k] for k in after}
        rows.append({"task_id": task["id"], "llm": llm.name, "config": cfg["name"],
                     "gold": task["answer"], "submitted": episode["answer"],
                     "passed": ok, "turns": episode["turns"], "status": episode["status"],
                     **usage})
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {task['id']:>4}  turns={episode['turns']}  "
              f"gold={task['answer']!r} got={episode['answer']!r}")

    n = len(rows)
    passed = sum(r["passed"] for r in rows)
    summary = {
        "config": cfg["name"], "llm": rows[0]["llm"] if rows else "-", "n": n,
        "pass_rate": round(passed / n, 3) if n else 0,
        "avg_turns": round(sum(r["turns"] for r in rows) / n, 2) if n else 0,
        "prompt_tokens": sum(r["prompt_tokens"] for r in rows),
        "completion_tokens": sum(r["completion_tokens"] for r in rows),
    }
    print("\n| config | llm | n | pass_rate | avg_turns | prompt_tok | compl_tok |")
    print("|---|---|---|---|---|---|---|")
    print(f"| {summary['config']} | {summary['llm']} | {n} | {summary['pass_rate']:.1%} "
          f"| {summary['avg_turns']} | {summary['prompt_tokens']} | {summary['completion_tokens']} |")

    out = Path(args.out or ROOT / "results" / f"{cfg['name']}-{summary['llm']}.jsonl")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nresults -> {out}")
    if args.fake:
        print("NOTE: --fake validates plumbing only; not a capability result.")


if __name__ == "__main__":
    main()
