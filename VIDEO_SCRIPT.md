# Video script — Assignment 8 Tier B (~4 minutes)

A short screen recording is required. Record with the IDE + a terminal + a browser visible.
Keep it to ~4 minutes. Suggested beats and things to say:

## 0:00 — Intro (20s)
"This is my Tier B project: an Afriland SME credit co-pilot — an orchestrator with five
specialist agents, a compliance gate, an evaluator that scores the architecture, and an
improvement loop. It runs offline with a mock model so it's fully reproducible."
- Show the repo tree in the IDE (`agents/`, `evaluator/`, `dashboard/`, `run.py`).

## 0:20 — The problem & design (40s)
- Open `README.md`, scroll the architecture diagram.
- "SME credit prep takes a week; the decision is quick. I automate the prep and keep the
  decision human. Five narrow agents, each with its own prompt and tools, writing to a
  per-case memory folder."
- Open `agents/specialists.py`, point at two system prompts (Compliance = can flag, never
  clear; Memo Writer = every figure from an artifact).

## 1:00 — Run the pipeline live (70s)
- In the terminal: `python run.py`
- Narrate the stages as they print:
  - Stage 0 single-agent benchmark — "no compliance screening, one log line."
  - Stage 1 multi-agent — "12 apps, 8 approve, 1 decline, **3 routed to compliance**."
  - Stage 2 evaluator — "**9.2/10**, throughput-limited."
  - Stage 3 optimize & re-run — "it bumps parallelism 1→4 and re-runs: **9.2 → 10.0**,
    3.4s → ~1.0s. That's the closed improvement loop."

## 2:10 — Memory & logs (40s)
- Open `memory/SME-003/` (Redline Trading) — show `03_compliance.json` with the sanctions
  flag and `decision.json` = `refer_compliance`. "The gate worked — it never reached approve."
- Run `python analyze_logs.py` — "~78 agent calls, zero errors; the evaluator reads these
  same logs to score observability."

## 2:50 — Board dashboard (50s)
- Open `dashboard/board_dashboard.html` in the browser.
- Walk the top cards (approved exposure XAF 278M, 3 compliance referrals, avg score 81,
  2× speedup), the decision-mix bars, the 9.2→10.0 self-score, and the per-application
  table with the compliance row highlighted.
- "Every number maps to a control or a decision — not AI slop."

## 3:40 — Reflection & close (30s)
- "What broke: my first evaluator scored 10 instantly, so I made the baseline genuinely
  sub-optimal to give the loop something to improve. Would I ship it? Not as-is — it needs
  real OCR, a governed sanctions feed and model-risk sign-off — but as a drafting assistant
  with a human approver, the shape is production-ready."
- End on the dashboard.

## Recording tips
- macOS: Shift-Cmd-5. Windows: Win-Alt-R (Xbox Game Bar) or OBS.
- Keep text large; zoom the terminal font. Trim dead air. MP4 is fine for Canvas.
