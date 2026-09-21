import json
from pathlib import Path

import yaml

from agent_databench.loop import run_episode
from agent_databench.scoring import score_answer

ROOT = Path(__file__).resolve().parent.parent


def _tasks():
    p = ROOT / "tasks" / "tasks.jsonl"
    if not p.exists():
        raise FileNotFoundError("run tasks/build_tasks.py first")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def test_fake_pipeline_end_to_end():
    cfg = yaml.safe_load((ROOT / "configs" / "base.yaml").read_text())
    tasks = _tasks()
    assert len(tasks) == 20
    for task in tasks[:3]:
        from agent_databench.llm import FakeLLM
        ep = run_episode(task, FakeLLM(task), cfg)
        assert ep["status"] == "submitted"
        assert score_answer(task, ep["answer"])


def test_scoring_rejects_wrong_answer():
    task = {"answer": 42.0, "kind": "float", "tol": 0.01}
    assert score_answer(task, "42.005")
    assert not score_answer(task, "43")
    assert not score_answer(task, None)
    assert not score_answer(task, "not a number")


def test_read_file_confined_to_data_dir():
    from agent_databench.tools import dispatch
    r = dispatch("read_file", {"path": "../tasks/build_tasks.py"})
    assert not r["ok"] and "escapes" in r["error"]
