"""
Orchestrator: owns case state and sequencing, dispatches specialist workers, enforces
the compliance hard-gate, and aggregates a portfolio-level result for the Board.

Fan-out happens at two levels:
  1. across applications (a thread pool sized by config['parallelism']), and
  2. within a case, the Financial Analyst and Compliance Officer run concurrently
     because neither depends on the other.
"""
from __future__ import annotations
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.specialists import (
    DocumentScout, FinancialAnalyst, ComplianceOfficer, RiskScorer, MemoWriter,
)
from tools import tools


class Orchestrator:
    def __init__(self, llm, logger, memory_root, config):
        self.llm, self.logger = llm, logger
        self.memory_root = memory_root
        self.config = config
        self.scout = DocumentScout(llm, logger)
        self.analyst = FinancialAnalyst(llm, logger)
        self.compliance = ComplianceOfficer(llm, logger)
        self.scorer = RiskScorer(llm, logger)
        self.memo = MemoWriter(llm, logger)

    # ---- one application end-to-end ----
    def process_case(self, application: dict) -> dict:
        case_id = application["id"]
        case_dir = os.path.join(self.memory_root, case_id)
        os.makedirs(case_dir, exist_ok=True)
        self.logger.log(agent="orchestrator", case_id=case_id, task="case_start")

        self.scout.run(case_id, case_dir, application)

        # fan-out within the case: financials || compliance
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_fut = ex.submit(self.analyst.run, case_id, case_dir, application)
            c_fut = ex.submit(self.compliance.run, case_id, case_dir, application)
            financials = f_fut.result()
            compliance = c_fut.result()

        # COMPLIANCE HARD GATE: cannot proceed to a decision while a flag is open
        if compliance.get("status") == "blocked":
            decision = {
                "id": case_id, "business_name": application["business_name"],
                "sector": application["sector"], "region": application["region"],
                "requested_amount": application["requested_amount"],
                "decision": "refer_compliance", "rating": None, "score": None,
                "pd": None, "flags": compliance.get("flags", []),
                "needs_human": True,
            }
            tools.write_memory(case_dir, "decision.json", decision)
            self.logger.log(agent="orchestrator", case_id=case_id,
                            task="compliance_gate", status="blocked",
                            flags=compliance.get("flags"))
            return decision

        risk = self.scorer.run(case_id, case_dir, application, financials)
        memo = self.memo.run(case_id, case_dir, application, financials, risk)

        decision = {
            "id": case_id, "business_name": application["business_name"],
            "sector": application["sector"], "region": application["region"],
            "requested_amount": application["requested_amount"],
            "decision": risk.get("recommendation"), "rating": risk.get("rating"),
            "score": risk.get("score"), "pd": risk.get("pd"),
            "dscr": financials.get("dscr"), "flags": compliance.get("flags", []),
            "memo": memo.get("summary"),
            # EVERY decision needs a human credit officer per policy
            "needs_human": True,
        }
        tools.write_memory(case_dir, "decision.json", decision)
        self.logger.log(agent="orchestrator", case_id=case_id, task="case_done",
                        decision=decision["decision"])
        return decision

    # ---- the batch (fan-out across applications) ----
    def run_batch(self, applications: list) -> dict:
        t0 = time.time()
        results = []
        workers = max(1, int(self.config.get("parallelism", 1)))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(self.process_case, a): a for a in applications}
            for fut in as_completed(futs):
                results.append(fut.result())
        wall = round(time.time() - t0, 2)
        results.sort(key=lambda r: r["id"])
        return self._aggregate(results, wall)

    def _aggregate(self, results, wall_seconds) -> dict:
        buckets = {"approve": 0, "refer": 0, "decline": 0, "refer_compliance": 0}
        exposure = {"approve": 0, "refer": 0, "decline": 0, "refer_compliance": 0}
        for r in results:
            d = r.get("decision", "refer")
            buckets[d] = buckets.get(d, 0) + 1
            exposure[d] = exposure.get(d, 0) + r.get("requested_amount", 0)
        scored = [r["score"] for r in results if r.get("score") is not None]
        return {
            "n_applications": len(results),
            "wall_seconds": wall_seconds,
            "parallelism": workers_used(self.config),
            "decision_counts": buckets,
            "exposure_by_decision": exposure,
            "approved_exposure": exposure["approve"],
            "avg_score": round(sum(scored) / len(scored), 1) if scored else None,
            "compliance_referrals": buckets["refer_compliance"],
            "cases": results,
        }


def workers_used(config):
    return max(1, int(config.get("parallelism", 1)))
