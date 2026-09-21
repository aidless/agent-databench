"""Sandboxed python execution: timeout, output cap, env stripping, temp cwd.

Deliberately NOT real isolation (no seccomp/nsjail). The README states this
honestly — interviewers ask exactly where the boundaries are.
"""
import os
import subprocess
import tempfile

MAX_OUTPUT = 4000  # chars kept per stream


def run_python(code: str, timeout: int = 15, cwd: str | None = None) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"  # stripped env may lack LANG; keep child stdout decodable
    use_cwd = cwd or tempfile.mkdtemp(prefix="databench-sb-")
    try:
        p = subprocess.run(
            ["python3", "-c", code],
            capture_output=True, text=True, timeout=timeout, env=env, cwd=use_cwd,
        )
        out, err, rc = p.stdout, p.stderr, p.returncode
        timed_out = False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = f"[killed after {timeout}s timeout]"
        rc, timed_out = -1, True
    return {
        "ok": rc == 0 and not timed_out,
        "returncode": rc,
        "stdout": out[:MAX_OUTPUT] + ("…[truncated]" if len(out) > MAX_OUTPUT else ""),
        "stderr": err[:MAX_OUTPUT] + ("…[truncated]" if len(err) > MAX_OUTPUT else ""),
        "timed_out": timed_out,
    }
