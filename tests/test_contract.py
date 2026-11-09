"""Drift guards: docs, CI, gold file, and the judge holes in FAILURE_MODES.md."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_databench.scoring import score_answer
from agent_databench.tools import dispatch

ROOT = Path(__file__).resolve().parent.parent
PYTEST_CMD = "python -m pytest tests/ -q"
GOLD_TASKS = 20
FIXTURE_ROWS = 40


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tasks():
    return [json.loads(line) for line in (ROOT / "tasks" / "tasks.jsonl").read_text().splitlines() if line.strip()]


def test_readme_problem_is_three_lines():
    lines = (ROOT / "README.md").read_text().splitlines()
    assert lines[0] == "# agent-databench"
    assert lines[1] == ""
    assert lines[2].startswith("[![CI](")
    assert lines[3] == ""
    assert lines[4:7] == [
        "A tool-calling agent answers one question about a CSV by running Python and submitting a string.",
        "The repo holds 20 questions with answers computed from a committed file of 40 data rows, and a harness that logs pass/fail, turns, and token counts.",
        "That is a measurement rig for this loop. It is not a general test of data analysis, and it does not include a live model score.",
    ]
    assert lines[7] == ""


def test_readme_separates_offline_and_live_paths():
    readme = (ROOT / "README.md").read_text()
    assert readme.index("## Offline path") < readme.index("## Live path")
    offline = readme.split("## Offline path", 1)[1].split("## Live path", 1)[0]
    live = readme.split("## Live path", 1)[1].split("## What a score does not prove", 1)[0]
    assert "--fake" in offline
    assert "LLM_API_KEY" not in offline
    assert "LLM_API_KEY" in live
    assert "requirements-live.txt" in live
    assert "no measured difference" in live
    assert "not a model score" in readme


def test_pytest_command_matches_across_readme_contributing_and_ci():
    for rel in ("README.md", "CONTRIBUTING.md", ".github/workflows/ci.yml"):
        assert PYTEST_CMD in (ROOT / rel).read_text(), rel
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "requirements-live" not in ci
    assert "LLM_API_KEY" not in ci
    assert "run.py" not in ci
    assert "make test" not in (ROOT / "CONTRIBUTING.md").read_text()


def test_documented_counts_match_fixture_and_builder():
    readme = (ROOT / "README.md").read_text()
    assert f"{GOLD_TASKS} questions" in readme
    assert f"{FIXTURE_ROWS} data rows" in readme
    bt = _load("build_tasks", "tasks/build_tasks.py")
    rows = bt.load_rows(ROOT / "data" / "games.csv")
    built = bt.build(rows)
    on_disk = _tasks()
    assert len(rows) == FIXTURE_ROWS
    assert bt.TASK_COUNT == GOLD_TASKS
    assert len(built) == GOLD_TASKS
    assert on_disk == built
    assert len({t["id"] for t in on_disk}) == GOLD_TASKS


def test_winner_column_matches_money_and_t20_is_not_the_tie_branch():
    bt = _load("build_tasks", "tasks/build_tasks.py")
    rows = bt.load_rows(ROOT / "data" / "games.csv")
    for row in rows:
        if row["money_a"] > row["money_b"]:
            assert row["winner"] == "a"
        elif row["money_b"] > row["money_a"]:
            assert row["winner"] == "b"
        else:
            assert row["winner"] == "tie"
    assert not any(row["winner"] == "tie" for row in rows)
    mean_a = bt.mean([row["money_a"] for row in rows])
    mean_b = bt.mean([row["money_b"] for row in rows])
    assert mean_a != mean_b
    task = next(item for item in _tasks() if item["id"] == "t20")
    assert task["answer"] == ("a" if mean_a > mean_b else "b")
    assert task["tol"] == 0.0


def test_failure_modes_examples_match_the_judge():
    by_id = {task["id"]: task for task in _tasks()}
    doc = (ROOT / "FAILURE_MODES.md").read_text()
    cases = [
        ("t11", "9.46", True),
        ("t11", "9.47", True),
        ("t11", "9.48", True),
        ("t11", "9.475", True),
        ("t11", "9.45", False),
        ("t11", "9.49", False),
        ("t02", "102850.875", True),
        ("t02", "102850.89", True),
        ("t02", "102850.87", False),
        ("t08", "0.42", True),
        ("t08", "0.425", True),
        ("t08", "0.43", False),
        ("t08", "0.41", False),
        ("t09", "169991.5", True),
        ("t09", "169991.6", False),
        ("t19", "1077115947.58", True),
        ("t19", "1077115947.59", False),
        ("t06", "17.0", True),
        ("t06", "1.7e1", True),
        ("t06", "17.0000000001", True),
        ("t06", "17.01", False),
    ]
    for task_id, submitted, accepted in cases:
        assert submitted in doc
        assert score_answer(by_id[task_id], submitted) is accepted
    assert by_id["t06"]["tol"] == 0.0
    assert by_id["t11"]["answer"] == 9.47
    assert by_id["t08"]["answer"] == 0.42
    assert score_answer(by_id["t12"], "671")
    assert score_answer(by_id["t12"], "671.0")
    assert "no live score" in doc


def test_integer_tol_field_is_applied():
    # The gold file stores 0. A hand-edited tol is not ignored.
    # 17.01 is not used here: abs(17.01 - 17) is slightly above 0.01 in float.
    assert score_answer({"answer": 17, "kind": "int", "tol": 0.01}, "17.005")
    assert not score_answer({"answer": 17, "kind": "int", "tol": 0.0}, "17.005")


def test_no_author_machine_paths():
    needles = ("Path." + "home(", "kagg_" + "decode", "\u4e0b\u8f7d")
    skip = {".git", ".venv", "__pycache__", ".pytest_cache"}
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in skip for part in path.parts):
            continue
        if path.suffix not in {".py", ".md", ".yml", ".yaml", ".txt", ".jsonl", ".csv", ".example"}:
            continue
        text = path.read_text(errors="replace")
        for needle in needles:
            if needle in text:
                offenders.append(f"{path.relative_to(ROOT)}: {needle}")
    assert offenders == []


def test_nested_pass_is_not_counted_as_an_action():
    bg = _load("build_games", "tasks/build_games_from_episodes.py")
    nested_pass = {"action": {"farmer": ["PASS"], "hands": [["PASS"], []], "market": []}}
    nested_act = {"action": {"farmer": ["PASS"], "hands": [["sow"]], "market": []}}
    assert bg.action_stats(nested_pass) == (1, 0)
    assert bg.action_stats(nested_act) == (0, 1)
    assert bg.action_stats({"action": {"hands": []}}) == (0, 0)
    assert bg.action_stats({}) == (0, 0)


def test_rebuild_does_not_overwrite_csv_when_the_dump_is_missing(tmp_path):
    bg = _load("build_games_main", "tasks/build_games_from_episodes.py")
    before = (ROOT / "data" / "games.csv").read_bytes()
    with pytest.raises(SystemExit):
        bg.main([str(tmp_path)])
    assert (ROOT / "data" / "games.csv").read_bytes() == before


def test_run_python_hides_gold_relatively_and_not_absolutely():
    relative = dispatch("run_python", {"code": "print(open('tasks/tasks.jsonl').read())"})
    assert not relative["ok"]
    assert "t01" not in relative["stdout"]
    copied = dispatch("run_python", {"code": "print(open('data/games.csv').readline())"})
    assert copied["ok"] and "episode_id" in copied["stdout"]
    gold = ROOT / "tasks" / "tasks.jsonl"
    absolute = dispatch("run_python", {"code": "print(open(%r).readline())" % str(gold)})
    assert absolute["ok"]
    assert "t01" in absolute["stdout"]


def test_committed_fake_log_matches_the_cli(tmp_path):
    out = tmp_path / "out.jsonl"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "--fake", "--out", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "not a capability result" in proc.stdout
    assert out.read_text() == (ROOT / "results" / "base-fake.jsonl").read_text()
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(rows) == GOLD_TASKS
    assert {row["llm"] for row in rows} == {"fake"}
    assert {row["note"] for row in rows} == {"plumbing only; not a model score"}
    assert all(row["passed"] for row in rows)
    assert sum(row["prompt_tokens"] + row["completion_tokens"] for row in rows) == 0
