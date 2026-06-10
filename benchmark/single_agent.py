"""
Single-agent benchmark -- the baseline you measure the multi-agent system against.

One generalist agent is asked to do the ENTIRE credit assessment for each application in
one shot. It is sequential, has no compliance hard-gate, no per-role memory, and no audit
trail beyond a single log line per case. This is intentionally the 'before' picture.
"""
from __future__ import annotations
import time
from agents.base import Agent


class GeneralistAgent(Agent):
    name = "generalist"
    system_prompt = (
        "You are a single generalist credit agent. For each SME application do everything "
        "at once: read documents, analyse financials, screen compliance, score risk and "
        "write the recommendation. Output strict JSON."
    )

    def assess(self, application, case_id):
        # the one-shot generalist still routes through risk_scoring math for comparability,
        # but with NO compliance gate and NO separate specialists.
        fin = self.ask("financial_analysis", application, case_id)
        payload = dict(application)
        payload.update({"dscr": fin.get("dscr"), "leverage": fin.get("leverage")})
        risk = self.ask("risk_scoring", payload, case_id)
        return {
            "id": case_id, "decision": risk.get("recommendation"),
            "score": risk.get("score"), "flags": [],  # generalist never screened -> blind spot
        }


def run_benchmark(llm, logger, applications):
    agent = GeneralistAgent(llm, logger)
    t0 = time.time()
    results = [agent.assess(a, a["id"]) for a in applications]
    wall = round(time.time() - t0, 2)
    # the benchmark's blind spot: it cannot have caught compliance hits
    return {
        "mode": "single_agent_baseline",
        "n_applications": len(results),
        "wall_seconds": wall,
        "compliance_screened": False,
        "audit_trail": "single log line per case",
        "results": results,
    }
