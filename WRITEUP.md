# Write-up — Assignment 8, Tier B

**Project:** Afriland SME Credit Origination Co-pilot — an orchestrator + 5 specialist
agents with a compliance hard-gate, file-based memory, fan-out, a Board dashboard, an
evaluator that scores the architecture, and a closed improvement loop. Runs offline.

## 1. The problem and the proposed solution

SME credit review at Afriland is bottlenecked at the front end — document gathering,
financial spreading, AML screening and memo drafting take 5–10 days per file, while the
actual credit decision is quick. **Why now:** LLMs are finally good enough to read messy
statements and produce structured, sourced analysis cheaply, so the preparation can be
automated *without* handing over the decision. The system automates preparation and leaves
the decision (and the accountability) with a human credit officer.

## 2. Single-agent benchmark (my baseline)

I first built one generalist agent that does the whole assessment in a single pass. It is
fast but has two structural problems: (a) **no compliance screening** — it never separates
that concern, so it cannot catch the sanctions/PEP/KYC cases; and (b) **no audit trail**
beyond one log line. On the 12-application batch it "approved" cases that the multi-agent
system correctly routes to compliance. The benchmark is the honest "before" picture I
measured everything else against.

## 3. Multi-agent design and whether it makes sense

An orchestrator owns case state and sequencing and dispatches five narrow specialists
(scout / analyst / compliance / scorer / writer). Each has its own short system prompt and
writes a JSON artifact into the case's memory folder. **Tools per agent are minimal and
deliberate** — the Compliance Officer calls a screening function (it must not *guess*),
the Analyst calls a benchmark lookup, the Writer calls nothing and only summarises existing
artifacts. Narrow roles + scoped context is exactly what kept the output from becoming
"AI slop": when I gave a single agent everything, its memo wandered; when each agent only
saw its slice, the outputs stayed tight and traceable.

## 4. Speeding it up: fan-out + evaluator-optimizer

Two levels of concurrency: Analyst and Compliance run together within a case (independent),
and the orchestrator fans out across applications with a configurable pool. Results are
aggregated by the orchestrator into a portfolio view (decision mix, exposure, average
score) for the Board.

## 5. Dashboard — is it real, or AI slop for the Board?

The dashboard reports things a Board actually governs by: approved exposure (XAF 278M of
403M requested), how many files were auto-blocked by compliance (3), the decision mix, the
average risk score, and the batch runtime vs. the single-agent baseline. It is intentionally
**not** a wall of charts — every number maps to a decision or a control. Honest answer:
v1 of the dashboard *was* slop (counts with no exposure, no compliance line); adding
exposure-at-risk and the compliance-referral count is what made it Board-worthy.

## 6. The evaluator agent and the improvement loop

An evaluator scores the architecture 1–10 on measurable signals (coverage, compliance
integrity, observability, error rate, throughput) and proposes one change. Run 1 scored
**9.2/10** and was throughput-limited; it recommended more parallelism. The optimizer
applied `parallelism: 1 → 4`, re-ran, and run 2 scored **10.0/10** at ~1.0s vs 3.4s.
That is a genuine closed loop — feedback captured, applied, and re-measured — not a
one-shot. The evaluator also notes the *next* gain is qualitative (an LLM-judge on memo
quality + a human-override capture loop), not more parallelism.

## 7. Logging and what the logs showed

Every agent call is a JSON line (agent, case, task, latency, status). `analyze_logs.py`
rolls them up: ~78 calls per full run, 0 errors, ~80ms/call. The logs are also what the
evaluator reads to compute observability and error rate — observability is wired into the
score, so the system is penalised if it stops logging.

## 8. What broke / what I'd change / was I confused?

- **What broke:** my first evaluator maxed at 10/10 immediately because simulated latency
  was tiny, so the "improvement loop" had nothing to improve. I had to make the baseline
  config genuinely sub-optimal (start sequential) so the loop could demonstrate a real
  before/after delta. Lesson: an evaluator is only useful if the starting point has
  visible headroom.
- **Confusion:** the within-case vs across-case concurrency interaction took a couple of
  tries to reason about cleanly; isolating fan-out into the orchestrator fixed it.
- **What I'd change next:** add the retry-with-backoff path (the evaluator already proposes
  it when errors appear), an LLM-judge on memo quality, and persist override reasons from
  the human officer to back-test AI-vs-human agreement.

## 9. Would I put this in enterprise production? Why / why not?

**Not as-is — but the shape is right.** The orchestration, compliance hard-gate, audit
trail and human-in-the-loop are production-shaped. What's missing for a regulated bank:
real OCR/extraction with confidence thresholds, a versioned and properly sourced
sanctions/PEP feed, model-risk governance and validation of the scorecard, access control
and PII handling, and human-factors testing to prevent rubber-stamping. I would deploy it
first as an **assistant that drafts** — never an auto-approver — measure agreement against
human officers, and only then widen its remit. The principle holds: automate the
preparation, keep the decision and its accountability human.
