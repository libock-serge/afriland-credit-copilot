"""
The four specialist workers + the memo writer.

Each agent has:
  - a narrow SYSTEM PROMPT (its job description / guardrails),
  - the tools it is allowed to use,
  - a run() that reads from and writes to the case's file-based memory.

Keeping prompts short and roles narrow is deliberate: it is what keeps a multi-agent
system from drifting into "AI slop". Each agent only sees what it needs.
"""
from __future__ import annotations
from .base import Agent
from tools import tools


class DocumentScout(Agent):
    name = "document_scout"
    system_prompt = (
        "You are a document intake agent for Afriland First Bank SME lending. "
        "Parse the applicant's submitted documents, confirm KYC completeness, and report "
        "an extraction confidence. NEVER invent a number you cannot read from a document; "
        "if a field is low-confidence, list it for human review. Output strict JSON."
    )

    def run(self, case_id, case_dir, application):
        result = self.ask("document_intake", application, case_id)
        tools.write_memory(case_dir, "01_extracted.json", result)
        return result


class FinancialAnalyst(Agent):
    name = "financial_analyst"
    system_prompt = (
        "You are a credit financial-analysis agent. Using only the extracted figures and "
        "the sector benchmark, compute net cash flow, DSCR, leverage and margin, and judge "
        "the trend. Show the inputs you used. Output strict JSON."
    )

    def run(self, case_id, case_dir, application):
        bench = tools.fetch_sector_benchmark(application.get("sector", ""))
        payload = dict(application)
        payload["sector_benchmark"] = bench
        result = self.ask("financial_analysis", payload, case_id)
        result["sector_benchmark"] = bench
        tools.write_memory(case_dir, "02_financials.json", result)
        return result


class ComplianceOfficer(Agent):
    name = "compliance_officer"
    system_prompt = (
        "You are an AML/compliance screening agent. Screen the borrower against sanctions "
        "and PEP lists and check KYC status. You may RAISE flags but you may never CLEAR a "
        "flag — a human compliance officer adjudicates. Output strict JSON."
    )

    def run(self, case_id, case_dir, application):
        payload = dict(application)
        # the agent calls a tool rather than guessing
        payload["sanctions_hit"] = tools.screen_sanctions(application.get("business_name", ""))
        result = self.ask("compliance", payload, case_id)
        tools.write_memory(case_dir, "03_compliance.json", result)
        return result


class RiskScorer(Agent):
    name = "risk_scorer"
    system_prompt = (
        "You are a risk-scoring agent. Combine the financial analysis into an internal "
        "rating, PD and a recommendation (approve / refer / decline). State the key drivers. "
        "A recommendation is advisory only. Output strict JSON."
    )

    def run(self, case_id, case_dir, application, financials):
        payload = dict(application)
        payload.update({
            "dscr": financials.get("dscr"),
            "leverage": financials.get("leverage"),
        })
        result = self.ask("risk_scoring", payload, case_id)
        tools.write_memory(case_dir, "04_risk.json", result)
        return result


class MemoWriter(Agent):
    name = "memo_writer"
    system_prompt = (
        "You are a credit-memo drafting agent. Write a concise, committee-ready summary "
        "from the upstream artifacts. Every figure must come from an artifact, not from you. "
        "Always state that a human credit officer must sign off. Output strict JSON."
    )

    def run(self, case_id, case_dir, application, financials, risk):
        payload = dict(application)
        payload.update({
            "dscr": financials.get("dscr"),
            "score": risk.get("score"), "rating": risk.get("rating"),
            "pd": risk.get("pd"), "recommendation": risk.get("recommendation"),
        })
        result = self.ask("memo", payload, case_id)
        tools.write_memory(case_dir, "05_memo.json", result)
        return result
