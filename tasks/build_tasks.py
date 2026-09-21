"""Generate tasks.jsonl: questions + answers computed directly from the CSV.

Answers are never hand-typed — the script is the single source of truth,
so the eval set can't silently rot when data changes.
"""
import csv
import json
import statistics
import sys
from pathlib import Path


def load_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["match_id"] = int(r["match_id"])
        for k in ("seed_count", "wheat_harvest", "corn_harvest", "beds_built"):
            r[k] = float(r[k])
        r["won"] = r["won"] == "yes"
    return rows


def mean(vals):
    return round(statistics.fmean(vals), 2)


def build(rows):
    red = [r for r in rows if r["team"] == "red"]
    blue = [r for r in rows if r["team"] == "blue"]
    wins = [r for r in rows if r["won"]]
    losses = [r for r in rows if not r["won"]]
    by_bed = {b: [r for r in rows if r["beds_built"] == b] for b in {r["beds_built"] for r in rows}}

    t = []

    def add(qid, question, answer, kind="float", tol=0.01):
        t.append({"id": qid, "question": question, "answer": answer, "kind": kind, "tol": tol})

    add("t01", "How many matches are in this dataset?", len(rows), "int")
    add("t02", "Mean wheat_harvest across all teams", mean([r["wheat_harvest"] for r in rows]))
    add("t03", "Mean wheat_harvest for team red", mean([r["wheat_harvest"] for r in red]))
    add("t04", "Mean wheat_harvest for team blue", mean([r["wheat_harvest"] for r in blue]))
    add("t05", "Difference in mean wheat_harvest, red minus blue",
        round(mean([r["wheat_harvest"] for r in red]) - mean([r["wheat_harvest"] for r in blue]), 2))
    add("t06", "Win rate of team red (fraction between 0 and 1)",
        round(len([r for r in red if r["won"]]) / len(red), 2))
    add("t07", "Win rate of team blue (fraction between 0 and 1)",
        round(len([r for r in blue if r["won"]]) / len(blue), 2))
    add("t08", "Median corn_harvest across all matches", statistics.median([r["corn_harvest"] for r in rows]))
    add("t09", "Mean corn_harvest in matches that were LOST", mean([r["corn_harvest"] for r in losses]))
    add("t10", "Mean corn_harvest in matches that were WON", mean([r["corn_harvest"] for r in wins]))
    add("t11", "Correlation (Pearson) between seed_count and wheat_harvest, rounded to 2 decimals",
        round(_pearson([r["seed_count"] for r in rows], [r["wheat_harvest"] for r in rows]), 2))
    add("t12", "Which team has the higher mean wheat_harvest? answer 'red' or 'blue'",
        "red" if mean([r["wheat_harvest"] for r in red]) > mean([r["wheat_harvest"] for r in blue]) else "blue",
        "str")
    add("t13", "Total beds_built across all matches", sum(r["beds_built"] for r in rows), "int")
    add("t14", "Mean seed_count per bed built (total seeds / total beds)",
        round(sum(r["seed_count"] for r in rows) / sum(r["beds_built"] for r in rows), 2))
    add("t15", "Match id with the highest wheat_harvest", max(rows, key=lambda r: r["wheat_harvest"])["match_id"], "int")
    add("t16", "Wheat harvest of match 7", [r for r in rows if r["match_id"] == 7][0]["wheat_harvest"])
    add("t17", "Number of matches where wheat_harvest > 50",
        len([r for r in rows if r["wheat_harvest"] > 50]), "int")
    add("t18", "Mean wheat_harvest for matches with exactly 7 beds built",
        mean([r["wheat_harvest"] for r in by_bed[7.0]]))
    add("t19", "Sum of corn_harvest for team blue matches that were won",
        round(sum(r["corn_harvest"] for r in blue if r["won"]), 2), "float", 0.05)
    add("t20", "Does mean corn_harvest go up or down with team red? answer 'up' or 'down' comparing "
               "red's mean corn_harvest vs blue's mean corn_harvest (answer 'up' if red is higher)",
        "up" if mean([r["corn_harvest"] for r in red]) > mean([r["corn_harvest"] for r in blue]) else "down",
        "str")
    return t


def _pearson(xs, ys):
    n = len(xs)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy)


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
