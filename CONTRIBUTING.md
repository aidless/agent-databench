# Contributing

Small, reviewable pull requests are welcome.

- One change per PR; describe what and why.
- Numbers in docs must be reproducible from a command in this repo. Do not add a pass rate, a turn count, a token cost, or a badge for a run that is not committed with its config, model id, and date. `run.py --fake` is not a model score.
- This repo has no package metadata and no publish workflow. Do not add a PyPI badge or a version badge for a release that does not exist.
- Do not commit secrets, datasets whose license is not stated from a source in the repo, or large binaries.
- Run `python -m pytest tests/ -q` before opening a PR. That is the command CI runs. There is no Makefile.
- Keep `README.md`, this file, and `.github/workflows/ci.yml` on that same pytest command.
- State limits in the same change as the feature. A documented hole beats a hidden one.
