"""LLM clients: real (OpenAI-compatible tool calling) + Fake (plumbing-only).

FakeLLM replays a scripted trajectory. It proves loop/tools/scoring wiring
works offline. It MUST NOT be used to make any capability claim — that
distinction is the whole point of the harness.
"""
import json
import os


class FakeLLM:
    name = "fake"

    def __init__(self, task: dict):
        self.task = task
        self.step = 0

    def chat(self, messages: list, tools: list) -> dict:
        self.step += 1
        if self.step == 1:
            code = (
                "import csv\n"
                "rows = list(csv.DictReader(open('data/games.csv')))\n"
                "print(len(rows))\n"
            )
            return {"content": "checking the dataset", "tool_calls": [
                {"id": "c1", "name": "run_python", "arguments": {"code": code}}]}
        return {"content": "done", "tool_calls": [
            {"id": "c2", "name": "submit_answer",
             "arguments": {"answer": str(self.task["answer"])}}]}

    @property
    def usage(self):
        return {"prompt_tokens": 0, "completion_tokens": 0}


class OpenAICompatLLM:
    name = "openai-compat"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL") or None,
        )
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0}

    @property
    def usage(self):
        return dict(self._usage)

    def chat(self, messages: list, tools: list) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools)
        u = resp.usage
        if u:
            self._usage["prompt_tokens"] += u.prompt_tokens or 0
            self._usage["completion_tokens"] += u.completion_tokens or 0
        msg = resp.choices[0].message
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
        return {"content": msg.content or "", "tool_calls": calls}


def make_llm(fake: bool, task: dict):
    if fake:
        return FakeLLM(task)
    return OpenAICompatLLM()
