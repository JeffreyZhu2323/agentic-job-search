# Recruiting Copilot

An agentic job-search system I built and run on [Claude Code](https://claude.com/claude-code): it tailors my resume to a job description with a multi-agent tournament, drafts personalized outreach, keeps a queryable application tracker, and, uniquely, **evaluates its own resume-tuning quality with a rigorous LLM-judge harness**. Everything is grounded in one honesty-boundary file so it never invents a claim.

This repo is the framework and a **fictional demo dataset** ("Jane Doe"). My real applications, contacts, and messages stay private, the committed data here is all placeholder.

> **What it demonstrates:** multi-agent orchestration, LLM-as-judge evaluation with bias controls, hook-based change detection, a schema-driven state machine, and human-in-the-loop honesty gating.

---

## The two things worth looking at first

### 1. A multi-agent tournament for the high-stakes tune (`/tune-resume-deep`)
For a dream company, the deep tune spends its budget on **breadth, not depth**: it spawns 4-6 subagents in parallel, each writing a full resume draft from a *different strategic angle* (agentic-systems-led, research-led, impact-led, keyword-aligned). It then picks the winner with a **pairwise comparison tournament** rather than numeric scores (LLMs compare "A vs B" far more reliably than they rate in isolation), refines it with a critic panel plus an explicit anti-pandering guard, and gates the whole thing behind a human review. Deterministic checks (one-page, ATS-parse-safety, an AI-tell blocklist) do the mechanical gating; agents judge only what a script can't.

### 2. An eval harness that measures whether any of this actually works (`eval/`)
Most "AI resume tools" are vibes. This one is evaluated. [`eval/DESIGN.md`](eval/DESIGN.md) + [`eval/README.md`](eval/README.md) specify experiments that answer, *with data*, whether the expensive deep tune earns its ~3-5x token cost and how to right-size it. The methodology hardens an LLM-judge proxy against its own failure modes:
- **Rubric-anchored** judging (ATS keywords, 6-second scan, hiring-manager credibility, JD-fit), not "which is better."
- **Deterministic sub-metrics** (`scripts/keyword_coverage.py`): keyword coverage %, one-page, and a **"gap leakage" check** that flags any keyword the candidate *can't* truthfully back (a fabrication red flag).
- **Cross-tier judge panel** (Opus + Sonnet), generators excluded from judging their own drafts, to blunt self-preference bias.
- **Order-bias control**: every comparison runs both A/B orders; a judge that flips on swap is scored a **tie**, not a win.
- Headline metric is **quality *per token***, not quality alone.

---

## The skills

| Command | What it does |
|---|---|
| `/tune-resume` | Fast single-pass tune for volume applications. Surfaces JD keywords from truthful content only, one-page ATS-safe, logs the application. |
| `/tune-resume-deep` | The multi-agent tournament above, for dream targets. |
| `/outreach` | Drafts a recruiter reply / cold outreach / referral ask / follow-up, tuned to the person. Draft-only (never sends); logs the touch + a verbatim thread. |
| `/sync-facts` | Reconciles the resume's source-of-truth against external ground-truth sources (a research-notes Google Doc, watched GitHub project repos) via content hashing. Approve-then-write. |
| `/check-map` + `/sync-docs` | A self-maintenance layer that detects and reconciles drift between the docs and the skills. |

Everything is grounded in `resume/Resume-Facts.md`, the **honesty boundary**: nothing is claimed unless it lives there, and the only thing that writes to it is a human-approved reconcile.

---

## Architecture

```
 /tune-resume, /tune-resume-deep, /outreach
        |
        v
 PreToolUse hook (sync-sources.sh)  ── content-hash change detection over
        |                              declared sources (Google Docs, GitHub repos)
        v                              + novelty scan for new files; ~free, no model
 skill reads the flag → reconcile facts only if a source moved (human-approved)
        |
        v
 tracker (data/, a schema-driven state machine)   eval/ (LLM-judge harness)
```

- **Hook-based change detection** is the deterministic, ~free half; the model-reasoning half runs only when a fingerprint actually moves, behind approval.
- **The tracker** ([`data/SCHEMA.md`](data/SCHEMA.md)) is three CSVs with a controlled vocabulary: applications (a status state machine), contacts, and an append-only outreach log paired with verbatim `threads/`.

---

## Repo layout

```
.claude/skills/     the agents (tune-resume, -deep, outreach, sync-facts, check-map, sync-docs)
.claude/hooks/      sync-sources.sh (change detection) + gh-claim-hash.sh
eval/               the LLM-judge evaluation harness (DESIGN, experiments, scorer)
data/               tracker schema + FICTIONAL sample CSVs (*.sample.csv) + a sample thread
resume/             Resume-Facts.sample.md + a compiled sample resume (fictional "Jane Doe")
companies/example/  a sample per-dream-target folder
CLAUDE.md           the orchestration layer (role, phrasing dials, honesty boundary)
```

The `*.sample.*` files and `companies/example/` are a fictional dataset so the repo reads end-to-end. Real applications, contacts, résumés, and notes are private and not committed.

---

## Notes
- **Outreach is draft-only.** It produces text and logs the touch; a human presses send.
- **The eval harness is designed, not yet run** (`eval/results/` is empty). Running experiment E1 (deep vs light) is the next step.

Built by Jeffrey Zhu. MIT licensed.
