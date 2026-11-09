# agent-databench

[![CI](https://github.com/aidless/agent-databench/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/agent-databench/actions/workflows/ci.yml)

A tool-calling agent answers one question about a CSV by running Python and submitting a string.
The repo holds 20 questions with answers computed from a committed file of 40 data rows, and a harness that logs pass/fail, turns, and token counts.
That is a measurement rig for this loop. It is not a general test of data analysis, and it does not include a live model score.

The CI badge is the offline pytest job in `.github/workflows/ci.yml`. It is not a model score. This repo has no package metadata and no publish workflow.

## Offline path

No API key. Inputs are the committed files `data/games.csv` (40 data rows) and `tasks/tasks.jsonl` (20 questions).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -q
.venv/bin/python run.py --fake
```

`python -m pytest tests/ -q` is the CI command (Python 3.12). The suite runs every gold task through `FakeLLM`, checks that `tasks/tasks.jsonl` matches `tasks/build_tasks.py` on the committed CSV, and pins the judge holes in `FAILURE_MODES.md`. It does not call a model.

`run.py --fake` writes `results/base-fake.jsonl`. Every row has `"llm": "fake"` and `"note": "plumbing only; not a model score"`, because `FakeLLM` submits the gold string on turn 2. A pass in that file means the loop, tool dispatch, and scorer are wired. Prompt and completion tokens in that file are 0 because the fake client reports no usage.

`requirements.txt` is pyyaml and pytest. The offline path does not import `openai` or pandas.

## Live path

This path needs an OpenAI-compatible endpoint. No live jsonl is checked in. Do not write a pass rate, a turn count, or a token cost into this README until the jsonl from that command is in the repo, with the model id and the date.

```bash
.venv/bin/pip install -r requirements-live.txt
cp .env.example .env
.venv/bin/python run.py --config configs/base.yaml
.venv/bin/python run.py --config configs/variant_tool_hints.yaml
```

`.env` needs `LLM_API_KEY`. `LLM_BASE_URL` and `LLM_MODEL` are optional. If `LLM_MODEL` is unset or blank, `agent_databench/llm.py` sends `deepseek-chat`. A blank `LLM_BASE_URL` leaves the client on the SDK default base URL. `requirements-live.txt` adds `openai` and `pandas`. The harness does not import pandas. It is installed so code the model writes can import it.

`configs/variant_tool_hints.yaml` appends three prompt lines about string columns, empty stdout, and state that does not persist between `run_python` calls. There is no measured difference between `base` and `tool_hints` in this repo.

## What a score does not prove

- A row with `"llm": "fake"`, including `results/base-fake.jsonl`, does not measure a model.
- A live `passed: true` means the submitted string met `score_answer`. The judge does not read the transcript, so it does not mean the method was right.
- `run_python` starts in a temp copy of `data/`. A relative open of `tasks/tasks.jsonl` fails. An absolute path can still read the answer key, `.env`, and any other file the OS user can read. A live pass does not prove the model computed the answer.
- These 20 questions are aggregations on one CSV: counts, means, one correlation, one seat label. There is no held-out set and no repeated trials, so there is no variance. A pass rate here is not a ranking of data-analysis skill.
- Token totals are the API usage object summed across calls. If that object is missing, the total stays 0. That is not a price.

The checked examples are in [FAILURE_MODES.md](FAILURE_MODES.md).

## Data

`data/games.csv` is the offline fixture. This checkout cannot rebuild it. The episode dump is not in the repo, and this README does not restate an upstream license or release date.

To rebuild from a dump you already have, then refresh the gold file:

```bash
.venv/bin/python tasks/build_games_from_episodes.py /path/to/episode_json_dir
.venv/bin/python tasks/build_tasks.py
```

`build_tasks.py` overwrites `tasks/tasks.jsonl`. The labels are that script. They are not a second annotation. Column definitions for the CSV live in `tasks/build_games_from_episodes.py`.

## Loop

`agent_databench/loop.py` keeps a message list, calls the client with three tools, and stops on `submit_answer` or after `max_turns` (8). Tool exceptions are appended as observations, and the episode continues until one of those two stops.

`read_file` may only read a file inside `data/`. `run_python` is a subprocess with a 15s timeout, a 4000-character output cap, and environment variables whose names contain `KEY`, `TOKEN`, `SECRET`, or `PASSWORD` removed. It is not a security boundary.

## Tests and counts

| What | Count | Locked by |
|---|---|---|
| Gold questions | 20 | `tasks/tasks.jsonl`, `TASK_COUNT` in `tasks/build_tasks.py`, pytest |
| Fixture data rows | 40 | `data/games.csv`, pytest |
| CI command | `python -m pytest tests/ -q` | `.github/workflows/ci.yml`, README, CONTRIBUTING |

The fake end-to-end test runs all 20 questions. Adding a test does not require an edit to CI. Changing the gold file without `build_tasks.py`, or changing the pytest command in only one of the README, CONTRIBUTING, and the workflow, fails the drift tests.
