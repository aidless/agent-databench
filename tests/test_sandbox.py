import os

from agent_databench.sandbox import run_python, MAX_OUTPUT


def test_timeout_kills_runaway():
    r = run_python("import time; time.sleep(5)", timeout=1)
    assert r["timed_out"] and not r["ok"]


def test_output_truncated():
    r = run_python("print('x' * 20000)")
    assert r["ok"]
    assert len(r["stdout"]) <= MAX_OUTPUT + 20  # cap + ellipsis marker
    assert "truncated" in r["stdout"]


def test_env_secrets_stripped(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-sup3rsecret")
    r = run_python("import os; print(os.environ.get('LLM_API_KEY'))")
    assert r["ok"] and "sup3rsecret" not in r["stdout"]


def test_plain_computation():
    r = run_python("print(6*7)")
    assert r["ok"] and r["stdout"].strip() == "42"
