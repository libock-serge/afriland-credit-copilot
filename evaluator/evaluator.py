"""
Evaluator agent + optimizer.

The evaluator scores the *architecture* of a run from 1-10 using measurable signals
(coverage, compliance-gate integrity, observability, error rate, throughput), explains
the score, and proposes a concrete improvement. The optimizer applies one improvement to
the config and the orchestrator re-runs -> a closed improvement loop with a measurable
before/after delta.
"""
from __future__ import annotations
import json
import os


def evaluate(run_summary: dict, log_path: str) -> dict:
    n = run_summary["n_applications"]
    cases = run_summary["cases"]

    # --- measurable signals ---
    decided = sum(1 for c in cases if c.get("decision"))
    coverage = decided / n if n else 0

    # observability: fraction of cases that have a full agent trail in the logs
    logged_cases = set()
    errors = 0
    total = 0
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            total += 1
            if rec.get("case_id"):
                logged_cases.add(rec["case_id"])
            if rec.get("status") == "error":
                errors += 1
    observability = len(logged_cases) / n if n else 0
    error_rate = errors / total if total else 0

    # compliance integrity: every flagged case must be referred, none auto-approved
    breaches = sum(1 for c in cases if c.get("flags") and c.get("decision") == "approve")
    compliance_ok = breaches == 0

    throughput = n / run_summary["wall_seconds"] if run_summary["wall_seconds"] else 0

    # --- score 1..10 ---
    score = 0.0
    score += 2.5 * coverage                       # all cases produce a decision
    score += 2.5 if compliance_ok else 0.0        # no compliance breach
    score += 2.0 * observability                  # full audit trail
    score += 1.5 * (1 - min(error_rate * 5, 1))   # low error rate
    score += min(1.5, throughput / 8 * 1.5)       # throughput headroom
    score = round(min(10.0, score), 1)

    # --- improvement proposal (what an AI reviewer would say) ---
    suggestions, patch = [], {}
    if throughput < 8 and run_summary["parallelism"] < 8:
        suggestions.append(
            "Throughput is the binding constraint. Increase batch parallelism to fan out "
            "across more applications concurrently.")
        patch["parallelism"] = min(8, max(4, run_summary["parallelism"] * 2))
    if error_rate > 0:
        suggestions.append("Add a single retry with backoff on agent errors to lift reliability.")
        patch["max_retries"] = 1
    if not suggestions:
        suggestions.append(
            "Architecture is sound. Next gain is qualitative: add an LLM-judge on memo "
            "quality and a human-override capture loop, not more parallelism.")

    return {
        "architecture_score": score,
        "signals": {
            "coverage": round(coverage, 2),
            "observability": round(observability, 2),
            "error_rate": round(error_rate, 3),
            "compliance_integrity": compliance_ok,
            "throughput_cases_per_s": round(throughput, 2),
        },
        "suggestions": suggestions,
        "proposed_patch": patch,
    }


def save_eval(eval_dir, run_id, payload):
    os.makedirs(eval_dir, exist_ok=True)
    path = os.path.join(eval_dir, f"eval_{run_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path
