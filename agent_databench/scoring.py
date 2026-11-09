"""Compare a submitted string to the gold field on a task.

kind "str" ignores tol (strip, case-insensitive).
Numeric kinds use abs(float(got) - float(gold)) <= max(tol, 1e-9).
Float rows default tol to 0.01 when the field is missing. Other numeric
kinds default it to 0, then the 1e-9 floor still applies.
This is an IEEE comparison, not a decimal-place rule. See FAILURE_MODES.md.
"""


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
    if kind == "float":
        tol = float(task.get("tol", 0.01))
    else:
        tol = float(task.get("tol", 0.0))
    return abs(got - float(gold)) <= max(tol, 1e-9)
