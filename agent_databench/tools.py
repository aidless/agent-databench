"""Tool definitions + dispatch. Paths are confined to the repo's data/ dir."""
from pathlib import Path

from .sandbox import run_python

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = (REPO_ROOT / "data").resolve()

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run python code in a sandbox (15s timeout, output capped). "
                           "Use it to load data/games.csv with the csv module or pandas and compute the answer.",
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
    target = (DATA_DIR / path).resolve()
    if not str(target).startswith(str(DATA_DIR)) or not target.is_file():
        raise ValueError(f"path escapes data/ or missing: {path!r}")
    return target.read_text()


def dispatch(name: str, args: dict) -> dict:
    if name == "run_python":
        # cwd at repo root so 'data/games.csv' resolves; see sandbox.py for
        # what is and isn't contained.
        return run_python(args["code"], cwd=str(REPO_ROOT))
    if name == "read_file":
        try:
            return {"ok": True, "content": read_data_file(args["path"])}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
    if name == "submit_answer":
        return {"ok": True, "submitted": args["answer"]}
    return {"ok": False, "error": f"unknown tool {name}"}
