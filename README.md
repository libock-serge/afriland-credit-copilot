# Afriland SME Credit Origination Co-pilot

A multi-agent system that triages a batch of SME loan applications for **Afriland First
Bank**: an **orchestrator** dispatches five **specialist agents**, enforces a hard
compliance gate, writes a per-applicant audit trail, aggregates a **Board dashboard**,
and runs an **evaluator → optimizer improvement loop** that scores its own architecture
and re-runs itself with the improvement applied.

> Built for *Applied AI in Finance — Assignment 8, Tier B (Autonomous Workflow II)*.

---

## TL;DR — run it

```bash
python run.py          # full pipeline: benchmark -> multi-agent -> evaluate -> optimize -> dashboard
python analyze_logs.py # per-agent call counts, latency, error rate from the structured logs
open dashboard/board_dashboard.html
```

No dependencies, no API key — it runs offline against a **deterministic mock model** so
the whole architecture (orchestration, memory, fan-out, evaluator loop, logging) executes
and produces real artifacts. Set `ANTHROPIC_API_KEY` (and `pip install anthropic`) to swap
the mock for a live model — nothing else changes.

---

## The business problem & why now

Afriland's SME credit review is slow at the *front end*: gathering documents, spreading
financials, screening compliance and drafting a memo takes 5–10 business days per file.
The decision itself is fast; the preparation is the bottleneck. With cheap, capable LLMs
now able to read messy statements and draft structured analysis, the preparation can be
automated **while the credit decision stays with a human officer**. That is the centaur
split this system implements.

## Architecture

```
                         ┌──────────────────────────────┐
   applications.json ───▶│        ORCHESTRATOR          │  owns case state + sequencing
                         │  (agents/orchestrator.py)    │  enforces the compliance gate
                         └───────────────┬──────────────┘  fans out across applications
                                         │
        ┌────────────────┬──────────────┼───────────────┬────────────────┐
        ▼                ▼              ▼                ▼                ▼
 Document Scout   Financial Analyst   Compliance     Risk Scorer     Memo Writer
   (intake/KYC)   (DSCR, leverage)    (AML/PEP gate) (rating, PD)    (committee draft)
        │  each agent has its own narrow system prompt + tools + writes to memory  │
        └──────────────── per-case memory folder: memory/SME-00X/*.json ───────────┘
                                         │
                          ┌──────────────▼───────────────┐
                          │   EVALUATOR  (1–10 score)    │ scores the architecture, then
                          │  proposes one improvement →  │ OPTIMIZER applies it & re-runs
                          └──────────────┬───────────────┘
                                         ▼
                              dashboard/board_dashboard.html
```

Financial Analyst and Compliance run **concurrently within a case** (independent), and the
orchestrator **fans out across applications** with a configurable pool. Compliance is a
**hard gate**: a flagged file (sanctions / PEP / incomplete KYC) can never reach `approve`.

## The five specialists (and why narrow roles)

| Agent | Tool(s) it uses | Reads → Writes |
|---|---|---|
| Document Scout | doc parse, KYC check | application → `01_extracted.json` |
| Financial Analyst | sector-benchmark lookup | extracted → `02_financials.json` |
| Compliance Officer | sanctions/PEP screening API | application → `03_compliance.json` |
| Risk Scorer | internal scorecard | financials → `04_risk.json` |
| Memo Writer | — (summarises artifacts) | all → `05_memo.json` |

Narrow prompts + per-role context are deliberate: it is what stops a multi-agent system
from drifting into "AI slop". Each agent only sees what its job needs.

## Memory

Each applicant gets a folder under `memory/SME-00X/`. Agents write structured JSON
artifacts there; downstream agents read them. The folder *is* the case's working memory
and its audit trail — every figure in the final memo traces back to a file.

## The improvement loop (evaluator → optimizer)

`evaluator/evaluator.py` scores each run 1–10 on **measurable** signals: coverage,
compliance integrity, observability (audit completeness), error rate and throughput. It
then proposes one concrete change. The driver applies the patch and re-runs:

```
v1: parallelism=1  ->  3.4s  ->  score 9.2/10  (throughput-limited)
    evaluator: "throughput is the binding constraint, raise parallelism"
v2: parallelism=4  ->  1.0s  ->  score 10.0/10  (+0.8)   ← closed loop, measured gain
```

## Single-agent benchmark

`benchmark/single_agent.py` is the baseline: one generalist agent does everything in one
shot — no compliance gate, no per-role memory, one log line per case. The multi-agent
system is ~2× faster on the batch **and** catches the 3 compliance cases the generalist is
structurally blind to. That contrast is the point of the benchmark.

## Logging & observability

Every agent call is one JSON line in `logs/run_*.jsonl` (agent, case, task, latency,
status). `analyze_logs.py` rolls these up. ~78 agent calls per full pipeline run.

## Layout

```
run.py                 # pipeline driver (the 5 stages)
analyze_logs.py        # log analysis
config.py              # paths + starting architecture config
llm/client.py          # mock + live model behind one interface
agents/                # base, specialists, orchestrator
tools/tools.py         # memory + simulated external tools
evaluator/evaluator.py # architecture scorer + optimizer patch
benchmark/             # single-agent baseline
dashboard/             # Board dashboard generator
data/applications.json # 12 simulated SME applications
WRITEUP.md             # reflection / what broke / production readiness
VIDEO_SCRIPT.md        # 4-minute screen-recording script
```

## Note on AI assistance

The specialist agents and the evaluator's improvement suggestion were generated with AI
help, as the assignment asks. The compliance hard-gate, the human-sign-off requirement and
the guardrails are deliberate design choices, not model output.
