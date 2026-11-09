import json
from pathlib import Path

import pytest
import yaml

from agent_databench.llm import FakeLLM
from agent_databench.loop import run_episode
from agent_databench.scoring import score_answer
from agent_databench.tools import read_data_file

ROOT = Path(__file__).resolve().parent.parent


def _tasks():
    path = ROOT / "tasks" / "tasks.jsonl"
    if not path.exists():
        raise FileNotFoundError("run tasks/build_tasks.py first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _base_cfg():
    return yaml.safe_load((ROOT / "configs" / "base.yaml").read_text())


def test_fake_pipeline_covers_every_gold_task():
    tasks = _tasks()
    assert len(tasks) == 20
    cfg = _base_cfg()
    for task in tasks:
        episode = run_episode(task, FakeLLM(task), cfg)
        assert episode["status"] == "submitted"
        assert episode["turns"] == 2
        assert episode["answer"] == str(task["answer"])
        assert score_answer(task, episode["answer"])


def test_fake_episode_passes_when_run_python_fails(monkeypatch):
    monkeypatch.setattr(
        "agent_databench.loop.dispatch",
        lambda name, args: {"ok": False, "error": "down"},
    )
    task = _tasks()[0]
    episode = run_episode(task, FakeLLM(task), _base_cfg())
    assert episode["status"] == "submitted"
    assert score_answer(task, episode["answer"])


def test_blank_llm_model_uses_the_documented_default(monkeypatch):
    from agent_databench.llm import configured_model
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert configured_model() == "deepseek-chat"
    monkeypatch.setenv("LLM_MODEL", "  ")
    assert configured_model() == "deepseek-chat"
    monkeypatch.setenv("LLM_MODEL", "demo-model")
    assert configured_model() == "demo-model"


def test_scoring_rejects_wrong_answer():
    task = {"answer": 42.0, "kind": "float", "tol": 0.01}
    assert score_answer(task, "42.005")
    assert not score_answer(task, "43")
    assert not score_answer(task, None)
    assert not score_answer(task, "not a number")


def test_read_file_confined_to_data_dir():
    from agent_databench.tools import dispatch
    result = dispatch("read_file", {"path": "../tasks/build_tasks.py"})
    assert not result["ok"] and "escapes" in result["error"]


def test_read_file_rejects_sibling_whose_name_shares_the_data_prefix(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "games.csv").write_text("ok\n")
    sibling = tmp_path / "data_backup"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("secret\n")
    monkeypatch.setattr("agent_databench.tools.DATA_DIR", data.resolve())
    assert read_data_file("games.csv") == "ok\n"
    with pytest.raises(ValueError, match="escapes"):
        read_data_file("../data_backup/secret.txt")
