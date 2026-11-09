# Failure modes

No live model transcript is stored in this repo. This file does not describe observed model mistakes. It describes ways the judge, the harness, or the gold file can make a result look better or worse than the calculation was.

The examples were checked against `data/games.csv` and `agent_databench/scoring.py`. `tests/test_contract.py` locks the same inputs. If you change the judge, update this file in the same commit.

## Judge false greens

`score_answer` parses the submission with `float` and accepts it when `abs(got - gold) <= tol`. `tol` is never tighter than `1e-9`. That is an IEEE comparison, not a rule about decimal places, and the two neighbors of a gold value are not treated symmetrically.

Checked on the current gold file:

| Task | Gold | Also accepted | Rejected |
|---|---|---|---|
| t11 mean `pass_turns_b` | 9.47 (`tol` 0.01) | `9.46`, `9.48`, and the exact mean `9.475` | `9.45`, `9.49` |
| t02 mean `money_a` | 102850.88 (`tol` 0.01) | exact mean `102850.875`, and `102850.89` | `102850.87` |
| t08 seat-a win rate | 0.42 (`tol` 0.01) | unrounded `0.425` (`17/40`) | `0.43`, `0.41` |
| t09 max money | 169991.0 (`tol` 0.5) | `169991.5` | `169991.6` |
| t19 mean seed | 1077115946.58 (`tol` 1.0) | `1077115947.58` (off by 1) | `1077115947.59` |
| t06 integer count | 17 (`tol` 0, floor `1e-9`) | `17.0`, `1.7e1`, `17.0000000001` | `17.01` |

t11 is the sharp case: three different two-decimal strings pass, so a pass does not mean the model produced `9.47`.

t19's tolerance is 1.0 on a mean the builder rounded to two decimals. The exact mean is `43084637863/40 = 1077115946.575`, so rounding moved it by 0.005. The tolerance is much wider than that. Off-by-one on the integer part still passes. The task file does not say why `tol` is 1.0.

Integer rows store `"tol": 0.0`. The `1e-9` floor still applies, and any string `float()` accepts is eligible, including scientific notation. A count of games can be submitted as `1.7e1`.

String rows (`t20`) ignore `tol`. Comparison is strip plus casefold, so `B` matches `b`. Extra words do not match.

The judge does not read the transcript. A correct string copied from the answer key, from a comment, or from an earlier print scores the same as a computation.

## Judge false reds

t08 asks for a win rate with "2 decimals". The exact rate is `17/40 = 0.425`.

- Half-up to two decimals is `0.43`. That submission fails, because `abs(0.43 - 0.42)` is slightly greater than `0.01` in float.
- Half-even, and `round(17/40, 2)` in CPython, is `0.42`. That is the gold, and it passes.
- The unrounded `0.425` passes.

The question does not name a rounding rule. A half-up answer is scored wrong. A pass on t08 does not mean "the unique two-decimal answer."

t11 splits the other way. The exact mean is `379/40 = 9.475`. Half-up to two decimals is `9.48`. CPython `round` returns `9.47` because the float is slightly under `9.475`, and `9.47` is the gold. Both strings pass, so half-up is a false green here rather than a false red. The label is still a float-round artifact, not a rule the question states.

## Harness false greens

`FakeLLM` in `agent_databench/llm.py` submits `str(task["answer"])` on its second call, after a `run_python` that only prints the row count. Scoring uses that string. If `run_python` returns an error, the fake episode still submits gold and still passes. `results/base-fake.jsonl` is that run. Every row passes. Every row has `"llm": "fake"` and `"note": "plumbing only; not a model score"`. Tokens are 0.

`run.py` prints a pass rate for the rows it just produced, including `--fake`. The rate is not filtered on `"llm"`. The process does print that `--fake` is not a capability result. A copied table that drops that line does not keep the caveat.

`run_python` runs in a temporary directory that contains a copy of `data/` and nothing else. `open("data/games.csv")` works. `open("tasks/tasks.jsonl")` does not. These still work, and a pass cannot rule them out:

- opening `tasks/tasks.jsonl` by absolute path, when the process can read it
- opening `.env` by absolute path
- any other file the OS user can read

There is no seccomp, no container, and no dropped filesystem. The timeout, the output cap, and the environment-name filter are the whole containment. The filter drops names containing `KEY`, `TOKEN`, `SECRET`, or `PASSWORD`. A secret under another name stays in the child environment. The child can still open a secret file by path.

`read_file` resolves the path and requires it to stay inside `data/`. A sibling directory whose name starts with `data` (for example `data_backup`) is rejected. That check is only on `read_file`.

A live response with no usage object leaves the token counters at 0 (`OpenAICompatLLM`). A 0 token total on a live row is not evidence the call was free.

`status: "submitted"` means `submit_answer` was called. It does not mean the answer passed. The summary pass rate uses the boolean from `score_answer`.

## Gold-label gaps

Labels are `tasks/build_tasks.py` applied to `data/games.csv`. The file the agent reads is the only source. There is no second annotator. A formula bug shared by the script and a straightforward solution is invisible. A bug in the CSV is invisible to every task.

`data/games.csv` was produced by `tasks/build_games_from_episodes.py`. The episode JSON is not in this repository, so the pass-turn and action-turn columns cannot be rechecked against the dump here. The tests check the flattener on synthetic nested actions. That does not validate the 40 committed rows.

On the committed CSV, the `winner` column matches a strict comparison of `money_a` and `money_b`, and there are no ties. The test locks that. It does not say the money values match an upstream reward.

`t20` labels the seat with the higher mean after each mean is rounded to two decimals. If those rounded means were equal, the script would label `b` even though the question asks which seat is higher. On this file the rounded means are `102850.88` and `104064.88`, and the unrounded means have the same order, so the tie branch is not the current label. The branch is still in the script.

`t08` and `t11` are the rounding gaps above. Other means on this file happen to agree between CPython `round(..., 2)` and half-up. Mean seat-a money `102850.875` goes to `102850.88` under both. That agreement is a property of these numbers, not a guarantee for the next CSV.

Each question is one aggregation. The set has no dirty rows, missing columns, joins, or held-out file. A high pass rate would not say anything about those.

## Not in this file

There is no base-versus-`tool_hints` delta, no model name, and no noise floor. Those need a live run committed with the config, the model id, and the date. Until then the summary is: no live score.
