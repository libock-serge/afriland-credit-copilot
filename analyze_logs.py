#!/usr/bin/env python3
"""Analyze the structured run logs: per-agent call counts, latency, error rate."""
from __future__ import annotations
import json
import glob
import os
from collections import defaultdict

import config


def analyze():
    files = sorted(glob.glob(os.path.join(config.LOG_DIR, "run_*.jsonl")))
    if not files:
        print("No logs found. Run: python run.py")
        return
    grand_calls = 0
    for path in files:
        per_agent = defaultdict(lambda: {"calls": 0, "latency": 0.0, "errors": 0})
        total, errors = 0, 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if "latency_ms" not in rec:
                    continue  # orchestrator state events
                a = rec.get("agent", "?")
                per_agent[a]["calls"] += 1
                per_agent[a]["latency"] += rec.get("latency_ms", 0)
                if rec.get("status") == "error":
                    per_agent[a]["errors"] += 1
                    errors += 1
                total += 1
        grand_calls += total
        print("\n" + os.path.basename(path))
        print(f"  {'agent':<20}{'calls':>7}{'avg ms':>10}{'errors':>9}")
        for a, s in sorted(per_agent.items()):
            avg = s["latency"] / s["calls"] if s["calls"] else 0
            print(f"  {a:<20}{s['calls']:>7}{avg:>10.1f}{s['errors']:>9}")
        print(f"  total agent calls: {total} | errors: {errors} | "
              f"error rate: {errors/total*100 if total else 0:.1f}%")
    print(f"\nGrand total agent calls across all runs: {grand_calls}")


if __name__ == "__main__":
    analyze()
