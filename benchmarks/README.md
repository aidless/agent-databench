# Benchmark: offline pipeline verification

`bench_pipeline.py` runs the real test suite and checks the committed `--fake`
replay result — no model, no network:

```bash
python benchmarks/bench_pipeline.py   # RESULT: PASS
```

| Check | What it proves |
|---|---|
| test suite | 7 tests pass (pipeline e2e, scoring rejection, sandbox 4 assertions) |
| committed replay | `results/base-fake.jsonl` has 20 rows, 20 passed, 20 distinct tasks, all `llm: fake` |

This is the honest claim the harness can make: the plumbing (loop/sandbox/scoring/
report) is verified end-to-end on 20 standard-answer tasks. Every row carries
`llm: fake`, so no capability number leaks into a claim. It does **not** claim any
real-model capability (see `PREREG.md` §5 boundaries).
