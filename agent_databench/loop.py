"""The agent loop: state = message list, one step = one LLM call + tool exec.

Failure handling is explicit: tool exceptions become observations (fed back),
max_turns ends the episode as a failure, and every step is recorded so the
harness can attribute failure modes after the run.
"""
import json

from .tools import TOOL_SPECS, dispatch


def run_episode(task: dict, llm, cfg: dict) -> dict:
    max_turns = cfg.get("max_turns", 8)
    system = cfg["system_prompt"]
    if cfg.get("tool_hints"):
        system += (
            "\n\nCommon failures to avoid:\n"
            "- Forgetting columns from csv.DictReader are strings: cast before math.\n"
            "- Printing nothing means the observation is empty; always print() the result.\n"
            "- Recomputing in a new run_python call is fine; state does not persist between calls.\n"
        )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task["question"] + "\n\nThe data file is data/games.csv."},
    ]
    transcript = []
    for turn in range(1, max_turns + 1):
        reply = llm.chat(messages, TOOL_SPECS)
        assistant_msg = {"role": "assistant", "content": reply["content"] or ""}
        if reply["tool_calls"]:
            assistant_msg["tool_calls"] = [_openai_call(c) for c in reply["tool_calls"]]
        messages.append(assistant_msg)
        if not reply["tool_calls"]:
            messages.append({"role": "user", "content": "You must call a tool. Prefer submit_answer when done."})
            transcript.append({"turn": turn, "event": "no_tool_call"})
            continue
        for call in reply["tool_calls"]:
            if call["name"] == "submit_answer":
                return {"answer": call["arguments"].get("answer"), "turns": turn,
                        "status": "submitted", "transcript": transcript}
            try:
                obs = dispatch(call["name"], call["arguments"])
            except Exception as e:  # tool bugs become observations, not crashes
                obs = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(obs, ensure_ascii=False, default=str)[:6000]})
            transcript.append({"turn": turn, "tool": call["name"], "ok": obs.get("ok")})
    return {"answer": None, "turns": max_turns, "status": "max_turns", "transcript": transcript}


def _openai_call(c):
    return {"id": c["id"], "type": "function",
            "function": {"name": c["name"], "arguments": json.dumps(c["arguments"], ensure_ascii=False)}}
