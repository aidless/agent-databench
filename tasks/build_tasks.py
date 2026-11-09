"""Generate tasks.jsonl from data/games.csv.

Answers are this script's outputs, not a separate annotation. Re-run it
when the CSV changes and commit the new jsonl with it. The drift test
fails if the file and build() diverge.

Non-float rows store tol 0. The scorer still has a 1e-9 floor.
"""

import csv
import json
import statistics
import sys
from pathlib import Path

NUM = ("seed", "act_timeout_s", "money_a", "money_b", "pass_turns_a",
       "pass_turns_b", "act_turns_a", "act_turns_b")
TASK_COUNT = 20


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
        if kind == "int":
            as_int = int(round(float(answer)))
            if abs(float(answer) - as_int) > 1e-9:
                raise ValueError(f"{qid} is not an integer value: {answer}")
            answer = as_int
            tol = 0.0
        elif kind != "float":
            tol = 0.0
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
    assert len(tasks) == TASK_COUNT, f"expected {TASK_COUNT} tasks, got {len(tasks)}"
    out = root / "tasks" / "tasks.jsonl"
    with open(out, "w") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    print(f"wrote {len(tasks)} tasks -> {out}")
    sys.exit(0)
