"""Scoring: compare episode answer vs gold from tasks.jsonl."""


def score_answer(task: dict, submitted) -> bool:
    if submitted is None:
        return False
    gold = task["answer"]
    kind = task.get("kind", "float")
    if kind == "str":
        return str(submitted).strip().lower() == str(gold).strip().lower()
    try:
        got = float(submitted)
    except (TypeError, ValueError):
        return False
    tol = float(task.get("tol", 0.01)) if kind == "float" else 0.0
    return abs(got - float(gold)) <= max(tol, 1e-9)
