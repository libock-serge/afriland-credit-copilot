"""Structured, append-only logging. Every agent call writes one JSON line."""
from __future__ import annotations
import json
import os
import time
import threading
from datetime import datetime, timezone

_LOCK = threading.Lock()


class RunLogger:
    def __init__(self, log_dir: str, run_id: str):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f"run_{run_id}.jsonl")
        self.run_id = run_id
        # truncate any prior file with this run id
        open(self.path, "w").close()

    def log(self, **fields):
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "run_id": self.run_id}
        rec.update(fields)
        line = json.dumps(rec, ensure_ascii=False)
        with _LOCK:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    # context manager to time + log a single agent call
    def call(self, agent, case_id, task):
        return _TimedCall(self, agent, case_id, task)


class _TimedCall:
    def __init__(self, logger, agent, case_id, task):
        self.logger, self.agent, self.case_id, self.task = logger, agent, case_id, task
        self.t0 = None

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        latency_ms = round((time.time() - self.t0) * 1000, 1)
        self.logger.log(
            agent=self.agent, case_id=self.case_id, task=self.task,
            latency_ms=latency_ms, status="error" if exc else "ok",
            error=str(exc) if exc else None,
        )
        return False  # never suppress exceptions
