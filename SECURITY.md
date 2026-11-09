# Security Policy

- Report vulnerabilities privately (a GitHub draft security advisory). Do not open a public issue with exploit details.
- This is a research codebase. There is no SLA and no bug-bounty program.
- CI runs `python -m pytest tests/ -q` only. It does not scan for secrets. Do not commit API keys, tokens, or private keys.
- `run_python` is a subprocess with a timeout and an output cap. It is not a sandbox. See `FAILURE_MODES.md`.
