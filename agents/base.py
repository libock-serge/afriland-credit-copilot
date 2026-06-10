"""Base agent: a system prompt + a set of tools + file-based memory + logged LLM calls."""
from __future__ import annotations
import json


class Agent:
    name = "agent"
    system_prompt = "You are a helpful specialist agent."

    def __init__(self, llm, logger):
        self.llm = llm
        self.logger = logger

    def ask(self, task: str, data: dict, case_id: str) -> dict:
        """One logged, timed LLM call. Returns parsed JSON (best effort)."""
        user = f"[TASK:{task}]\n[DATA]\n{json.dumps(data, ensure_ascii=False)}"
        with self.logger.call(self.name, case_id, task):
            raw = self.llm.complete(self.system_prompt, user, json_mode=True)
        try:
            return json.loads(raw)
        except Exception:
            return {"_raw": raw}
