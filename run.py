#!/usr/bin/env python3
"""
Afriland SME Credit Origination Co-pilot — full pipeline driver.

Stages (each prints to the console and writes artifacts to disk):
  0. Single-agent BENCHMARK            -> your baseline
  1. Multi-agent run (orchestrator + 5 specialists, fan-out, compliance gate)
  2. EVALUATE the architecture (1-10) + get an improvement proposal
  3. OPTIMIZE: apply the proposed patch and RE-RUN  -> closed improvement loop
  4. Build the Board dashboard
  5. (analyze_logs.py reads the structured logs)

Runs fully offline with a deterministic mock model. Set ANTHROPIC_API_KEY to run live.
"""
from __future__ import annotations
import json
import shutil
import time
import os

import config
from core.obs import RunLogger
from llm.client import get_llm
from agents.orchestrator import Orchestrator
from benchmark.single_agent import run_benchmark
from evaluator.evaluator import evaluate, save_eval
from dashboard.build_dashboard import render


def load_applications():
    with open(config.DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fresh(path):
    """Empty a directory's contents without removing the dir itself (mount-safe)."""
    os.makedirs(path, exist_ok=True)
    for entry in os.listdir(path):
        p = os.path.join(path, entry)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except (PermissionError, OSError):
            pass


def banner(t):
    print("\n" + "=" * 64 + f"\n{t}\n" + "=" * 64)


def main():
    apps = load_applications()
    fresh(config.MEMORY_ROOT)
    fresh(config.LOG_DIR)
    llm = get_llm()
    mode = "LIVE (Anthropic)" if os.environ.get("ANTHROPIC_API_KEY") else "OFFLINE (deterministic mock)"
    print(f"Model mode: {mode}  |  {len(apps)} SME applications")

    # ---- Stage 0: single-agent benchmark ----
    banner("STAGE 0 - SINGLE-AGENT BENCHMARK (baseline)")
    bench_logger = RunLogger(config.LOG_DIR, "benchmark")
    baseline = run_benchmark(llm, bench_logger, apps)
    print(f"  baseline time: {baseline['wall_seconds']}s | compliance screened: "
          f"{baseline['compliance_screened']} | audit: {baseline['audit_trail']}")

    # ---- Stage 1: multi-agent run ----
    banner("STAGE 1 - MULTI-AGENT RUN (orchestrator + 5 specialists)")
    cfg = dict(config.INITIAL_CONFIG)
    logger1 = RunLogger(config.LOG_DIR, "v1")
    orch1 = Orchestrator(llm, logger1, config.MEMORY_ROOT, cfg)
    run1 = orch1.run_batch(apps)
    print(f"  parallelism={cfg['parallelism']} | time={run1['wall_seconds']}s | "
          f"decisions={run1['decision_counts']}")

    # ---- Stage 2: evaluate architecture ----
    banner("STAGE 2 - EVALUATOR AGENT (architecture score 1-10)")
    eval1 = evaluate(run1, logger1.path)
    save_eval(config.EVAL_DIR, "v1", eval1)
    print(f"  architecture score: {eval1['architecture_score']}/10")
    print(f"  signals: {json.dumps(eval1['signals'])}")
    for s in eval1["suggestions"]:
        print(f"   - suggestion: {s}")

    # ---- Stage 3: optimize + re-run (the improvement loop) ----
    banner("STAGE 3 - OPTIMIZE & RE-RUN (improvement loop)")
    patch = eval1["proposed_patch"]
    cfg2 = dict(cfg)
    cfg2.update(patch)
    print(f"  applying patch: {patch or '(none)'}  -> new config {cfg2}")
    logger2 = RunLogger(config.LOG_DIR, "v2")
    fresh(config.MEMORY_ROOT)
    orch2 = Orchestrator(llm, logger2, config.MEMORY_ROOT, cfg2)
    run2 = orch2.run_batch(apps)
    eval2 = evaluate(run2, logger2.path)
    save_eval(config.EVAL_DIR, "v2", eval2)
    delta = round(eval2["architecture_score"] - eval1["architecture_score"], 1)
    sign = "+" if delta >= 0 else ""
    print(f"  v2 time={run2['wall_seconds']}s | score {eval1['architecture_score']} -> "
          f"{eval2['architecture_score']} (delta {sign}{delta})")

    # ---- Stage 4: Board dashboard ----
    banner("STAGE 4 - BOARD DASHBOARD")
    out = render(run2, eval1, eval2, baseline, config.DASHBOARD_FILE)
    print(f"  wrote {out}")

    # ---- run-level summary artifact ----
    speedup = round(baseline["wall_seconds"] / run2["wall_seconds"], 2) if run2["wall_seconds"] else None
    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "baseline_seconds": baseline["wall_seconds"],
        "v1": {"config": cfg, "seconds": run1["wall_seconds"],
               "score": eval1["architecture_score"], "decisions": run1["decision_counts"]},
        "v2": {"config": cfg2, "seconds": run2["wall_seconds"],
               "score": eval2["architecture_score"], "decisions": run2["decision_counts"]},
        "score_delta": delta,
        "speedup_vs_baseline": speedup,
    }
    out_path = os.path.join(config.BASE, "run_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    banner("DONE")
    print("  run_summary.json, dashboard/board_dashboard.html, logs/, memory/ all written.")
    print("  Next: python analyze_logs.py")


if __name__ == "__main__":
    main()
