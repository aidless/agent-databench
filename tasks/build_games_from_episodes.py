#!/usr/bin/env python3
"""Flatten a local episode dump into data/games.csv.

The dump is not in this repository. Pass its directory on the command line.
Offline runs use the committed data/games.csv and do not execute this script.
Column values are computed here. This file does not record an upstream
license or release date, because the dump is not here to check.
"""
import argparse
import csv
import json
import sys
from pathlib import Path


def _flatten_cmds(a) -> list[str]:
    """Episode actions are nested: {farmer:[...], hands:[[...],[...]], market:[...]}"."""
    if a is None:
        return []
    if isinstance(a, str):
        return [a]
    if isinstance(a, list):
        return [c for x in a for c in _flatten_cmds(x)]
    if isinstance(a, dict):
        return [c for v in a.values() for c in _flatten_cmds(v)]
    return [str(a)]


def action_stats(agent_step) -> tuple[int, int]:
    """Return (pass_count, nonpass_count) contribution for one agent one step."""
    cmds = [c for c in _flatten_cmds(agent_step.get("action")) if c.strip()]
    if not cmds:
        return 0, 0  # timeout/no-response: neither pass nor real action
    if all(c.strip().upper() == "PASS" for c in cmds):
        return 1, 0
    return 0, 1


def flatten(path: Path) -> dict:
    d = json.loads(path.read_text())
    last = d["steps"][-1]
    teams = d["info"].get("TeamNames") or ["team_a", "team_b"]
    ma, mb = last[0].get("reward", 0.0), last[1].get("reward", 0.0)
    pa = sum(action_stats(s[0])[0] for s in d["steps"])
    na = sum(action_stats(s[0])[1] for s in d["steps"])
    pb = sum(action_stats(s[1])[0] for s in d["steps"])
    nb = sum(action_stats(s[1])[1] for s in d["steps"])
    return {
        "episode_id": d.get("id") or path.stem,
        "seed": d["info"].get("seed") or d["configuration"].get("seed") or -1,
        "act_timeout_s": d["configuration"].get("actTimeout", -1),
        "team_a": teams[0], "team_b": teams[1],
        "money_a": round(float(ma), 1), "money_b": round(float(mb), 1),
        "winner": "a" if ma > mb else ("b" if mb > ma else "tie"),
        "pass_turns_a": pa, "pass_turns_b": pb,
        "act_turns_a": na, "act_turns_b": nb,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "episodes_dir",
        type=Path,
        help="Directory of episode *.json files. Not shipped in this repo.",
    )
    ap.add_argument(
        "-n",
        type=int,
        default=40,
        help="Max files to read, after sorting by name (default: 40).",
    )
    args = ap.parse_args(argv)
    files = sorted(args.episodes_dir.glob("*.json"))[: args.n]
    if not files:
        sys.exit(f"no episode json files under {args.episodes_dir}")
    out = Path(__file__).resolve().parent.parent / "data" / "games.csv"
    rows = [flatten(p) for p in files]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} games -> {out}")


if __name__ == "__main__":
    main()
