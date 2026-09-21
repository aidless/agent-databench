#!/usr/bin/env python3
"""Flatten official episode dumps (read-only) into data/games.csv.

Source: ~/下载/kagg_decode/external/eps_top10/*.json  (Kaggle CC0 episode dump,
publicly released 2026-09-19). Columns are computed HERE, fresh — this demo's
numbers are never copied from any competition ledger.
"""
import csv
import json
import sys
from pathlib import Path

EPISODES = Path.home() / "下载/kagg_decode/external/eps_top10"


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


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    files = sorted(EPISODES.glob("*.json"))[:n]
    if not files:
        sys.exit(f"no episodes under {EPISODES}")
    out = Path(__file__).resolve().parent.parent / "data" / "games.csv"
    rows = [flatten(p) for p in files]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} games -> {out}")


if __name__ == "__main__":
    main()
