"""Tool definitions + dispatch.

read_file stays inside data/. run_python does not: it is a subprocess in a
temp directory that holds a copy of data/ and nothing else. Absolute paths
can still read the rest of the machine. See FAILURE_MODES.md.
"""
import shutil
import tempfile
from pathlib import Path

from .sandbox import run_python

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = (REPO_ROOT / "data").resolve()

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run python in a subprocess (15s timeout, output capped). "
                           "The working directory contains data/games.csv. "
                           "Load it with the csv module or pandas and compute the answer.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "python source to execute"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file under data/ (only data/ is reachable). Returns its text.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "filename relative to data/, e.g. games.csv"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_answer",
            "description": "Submit the final answer for the question and end the episode.",
            "parameters": {
                "type": "object",
                "properties": {"answer": {"type": "string", "description": "the final answer, number or short text"}},
                "required": ["answer"],
            },
        },
    },
]


def read_data_file(path: str) -> str:
    root = DATA_DIR.resolve()
    # An absolute `path` drops `root` on join. is_relative_to still rejects it.
    # startswith(root) would accept a sibling such as data_backup/.
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"path escapes data/ or missing: {path!r}")
    return target.read_text()


def dispatch(name: str, args: dict) -> dict:
    if name == "run_python":
        with tempfile.TemporaryDirectory(prefix="databench-ws-") as workspace:
            shutil.copytree(DATA_DIR, Path(workspace) / "data")
            return run_python(args["code"], cwd=workspace)
    if name == "read_file":
        try:
            return {"ok": True, "content": read_data_file(args["path"])}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
    if name == "submit_answer":
        return {"ok": True, "submitted": args["answer"]}
    return {"ok": False, "error": f"unknown tool {name}"}
