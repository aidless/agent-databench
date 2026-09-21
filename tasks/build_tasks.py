"""Generate tasks.jsonl: questions + answers computed directly from the CSV.

Answers are never hand-typed — the script is the single source of truth,
so the eval set can't silently rot when data changes.
Schema: official Kaggriculture episode dumps flattened by
build_games_from_episodes.py (money/win/pass/act columns per seat).
"""
import csv
import json
import statistics
import sys
from pathlib import Path

NUM = ("seed", "act_timeout_s", "money_a", "money_b", "pass_turns_a",
       "pass_turns_b", "act_turns_a", "act_turns_b")


def load_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in NUM:
            r[k] = float(r[k])
    return rows


def mean(vals):
    return round(statistics.fmean(vals), 2)


def _pearson(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy)


def build(rows):
    t = []

    def add(qid, question, answer, kind="float", tol=0.01):
        t.append({"id": qid, "question": question, "answer": answer, "kind": kind, "tol": tol})

    margin = [r["money_a"] - r["money_b"] for r in rows]
    add("t01", "How many games are in this dataset?", len(rows), "int")
    add("t02", "Mean final money for seat a", mean([r["money_a"] for r in rows]))
    add("t03", "Mean final money for seat b", mean([r["money_b"] for r in rows]))
    add("t04", "Mean money difference, seat a minus seat b", mean(margin))
    add("t05", "Median final money for seat a", round(statistics.median([r["money_a"] for r in rows]), 2))
    add("t06", "How many games did seat a win? (winner column says 'a')",
        len([r for r in rows if r["winner"] == "a"]), "int")
    add("t07", "How many games ended in a tie? (winner column 'tie')",
        len([r for r in rows if r["winner"] == "tie"]), "int")
    add("t08", "Win rate of seat a (fraction between 0 and 1, 2 decimals)",
        round(len([r for r in rows if r["winner"] == "a"]) / len(rows), 2))
    add("t09", "Highest single-game money across BOTH seats",
        max(max(r["money_a"], r["money_b"]) for r in rows), "float", 0.5)
    add("t10", "Mean pass-only turns for seat a (column pass_turns_a)",
        mean([r["pass_turns_a"] for r in rows]))
    add("t11", "Mean pass-only turns for seat b", mean([r["pass_turns_b"] for r in rows]))
    add("t12", "Total pass-only turns across both seats all games",
        sum(r["pass_turns_a"] + r["pass_turns_b"] for r in rows), "int")
    add("t13", "Mean active turns for seat a (column act_turns_a)",
        mean([r["act_turns_a"] for r in rows]))
    add("t14", "Correlation (Pearson) between pass_turns_a and money_a, 2 decimals",
        round(_pearson([r["pass_turns_a"] for r in rows], [r["money_a"] for r in rows]), 2))
    add("t15", "Largest absolute money margin in one game", round(max(abs(m) for m in margin), 2))
    add("t16", "Mean absolute money margin", mean([abs(m) for m in margin]))
    add("t17", "How many games did seat a finish above $100,000?",
        len([r for r in rows if r["money_a"] > 100000]), "int")
    add("t18", "How many games had seat a pass-only turns above 5?",
        len([r for r in rows if r["pass_turns_a"] > 5]), "int")
    add("t19", "Mean seed value of the games", mean([r["seed"] for r in rows]), "float", 1.0)
    add("t20", "Which seat has the higher mean money overall? answer 'a' or 'b'",
        "a" if mean([r["money_a"] for r in rows]) > mean([r["money_b"] for r in rows]) else "b", "str")
    return t


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    rows = load_rows(root / "data" / "games.csv")
    tasks = build(rows)
    assert len(tasks) == 20, f"expected 20 tasks, got {len(tasks)}"
    out = root / "tasks" / "tasks.jsonl"
    with open(out, "w") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    print(f"wrote {len(tasks)} tasks -> {out}")
    sys.exit(0)
