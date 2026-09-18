# Recruiting Copilot

An agentic job-search system I built and run on [Claude Code](https://claude.com/claude-code). It tailors my resume to a job description with a multi-agent tournament, reads my recruiting inbox through a read-only Gmail integration and proposes the tracker updates for me to approve, drafts outreach in my own voice, and keeps a queryable application tracker. It also ships with the thing most "AI resume tools" skip: an **LLM-judge eval harness built to measure whether its own output is actually better**. Every claim it can make is grounded in one honesty-boundary file, so it never invents a credential.

This repo is the framework plus a **fictional demo dataset** ("Jane Doe"). My real applications, contacts, and messages stay private; everything committed here is placeholder.

> **What it demonstrates:** multi-agent orchestration, LLM-as-judge evaluation with bias controls, a scope-locked read-only MCP integration, deterministic hook-based gating (change detection plus an AI-tell linter), a schema-driven state machine, and human-in-the-loop honesty gating.

---

## The parts worth looking at first

### 1. A multi-agent tournament for the high-stakes tune (`/tune-resume-deep`)
For a dream company the deep tune spends its budget on **breadth, not depth**. It spawns 4-6 subagents in parallel, each writing a full resume draft from a different strategic angle (agentic-systems-led, research-led, impact-led, keyword-aligned). It then picks the winner with a **pairwise comparison tournament** rather than numeric scores, because LLMs compare "A vs B" far more reliably than they rate a single item in isolation. The winner goes through a critic panel with an explicit anti-pandering guard, then a human review. Deterministic checks (one-page, ATS-parse-safety, an AI-tell blocklist) do the mechanical gating; agents judge only what a script can't.

### 2. An eval harness built to measure whether any of this works (`eval/`)
Most "AI resume tools" run on vibes. This one is built to be checked. The scorer is implemented and the methodology is fully specified in [`eval/DESIGN.md`](eval/DESIGN.md) and [`eval/README.md`](eval/README.md); the experiments are set up but **not yet run** (that's the honest status). They're designed to answer, with data, whether the expensive deep tune earns its ~3-5x token cost and how to right-size it. The methodology hardens an LLM-judge proxy against its own failure modes:
- **Rubric-anchored** judging (ATS keywords, 6-second scan, hiring-manager credibility, JD-fit), not a vague "which is better."
- **Deterministic sub-metrics** (`eval/scripts/keyword_coverage.py`): keyword coverage % and a **gap-leakage check** that flags any keyword the candidate can't truthfully back (a fabrication red flag). One-page and ATS-parse safety are checked by script too.
- **Cross-tier judge panel** (Opus + Sonnet), with generators excluded from judging their own drafts, to blunt self-preference bias.
- **Order-bias control**: every comparison runs in both A/B orders; a judge that flips on swap is scored a **tie**, not a win.
- The headline metric is **quality per token**, not quality alone.

### 3. A read-only Gmail integration that triages my inbox (`/inbox` + a custom MCP server)
Rather than wire in an off-the-shelf Gmail server, I wrote a small [MCP server](tools/gmail-mcp/) so I could lock down exactly what it can do. The OAuth scope is `gmail.readonly`, so the token **physically cannot send, label, or delete**, and it reads only my `Recruiting` label, so the agent never touches the rest of my inbox. OAuth secrets live outside the repo. On `/inbox` the skill reads each new message, classifies it, and quotes the sentence that justifies its read, then proposes one consolidated set of tracker updates across applications, contacts, and the outreach log. The action space is wide (a status move, a new contact, a logged reply, a flagged deadline, a handoff to a resume tune), but **every write clears one human approval**. An idempotent watermark of processed message IDs keeps re-runs from double-counting.

---

## The skills

| Command | What it does |
|---|---|
| `/tune-resume` | Fast single-pass tune for volume applications. Surfaces JD keywords from truthful content only, one-page and ATS-safe, then logs the application. |
| `/tune-resume-deep` | The multi-agent tournament above, for dream targets. |
| `/inbox` | Reads new mail in my `Recruiting` label through the read-only MCP server, classifies each message, and proposes tracker updates for approval. Manual-only; never sends. |
| `/outreach` | Drafts a recruiter reply, cold outreach, referral ask, or follow-up, tuned to the person. Draft-only (never sends); logs the touch plus a verbatim thread. |
| `/sync-facts` | Reconciles the resume's source-of-truth against external ground-truth sources (a research-notes Google Doc, watched GitHub repos) via content hashing. Approve-then-write. |
| `/check-map` + `/sync-docs` | A self-maintenance layer that detects and reconciles drift between the docs and the skills themselves. |

Everything is grounded in `resume/Resume-Facts.md`, the **honesty boundary**: nothing is claimed unless it lives there, and the only thing that writes to it is a human-approved reconcile.

---

## Architecture

```
 resume / outreach                             inbox triage
 /tune-resume  /tune-resume-deep  /outreach     /inbox
        |                                          |
        v                                          v
 sync-sources hook (deterministic, ~free):   gmail-recruiting MCP server
   content-hash declared sources               read-only (gmail.readonly),
   (Google Docs, GitHub) + novelty scan        Recruiting label only
        |                                          |
        v                                          v
 reconcile facts only if a source moved     classify + match each message
 (human-approved)                            to a tracker row, propose updates
        |                                          |
        +--------------------+---------------------+
                             v
        tracker (data/): a schema-driven state machine
        applications (status) · contacts · outreach log + verbatim threads
                             |
                             v
        eval/: LLM-judge harness, scoring tune quality per token
```

Three ideas run through all of it:
- **Deterministic where a script can do the job, model where it can't.** Change detection, keyword coverage, one-page and ATS checks, and the AI-tell linter are plain code, near-free and repeatable. The model runs only where judgment is actually needed, and behind approval. Voice is layered the same way: the AI-tell linter is the deterministic floor, and above it a voice spec with real writing samples anchors the prose while a voice-critic agent in the tournament judges whether a draft actually reads like a person.
- **The tracker** ([`data/SCHEMA.md`](data/SCHEMA.md)) is three CSVs with a controlled vocabulary: applications (a status state machine), contacts, and an append-only outreach log paired with verbatim `threads/`.
- **The system maintains itself.** `/check-map` mechanically flags drift between the docs and the skills (a skill missing from the map, a broken path), and `/sync-docs` reconciles it behind approval, so the documentation can't quietly rot as the skills change.

---

## Repo layout

```
.claude/skills/     the skills: tune-resume, tune-resume-deep, inbox, outreach,
                    sync-facts, check-map, sync-docs
.claude/hooks/      sync-sources.sh (source change detection), gh-claim-hash.sh,
                    voice-lint.py (blocks a resume write carrying AI-writing tells)
tools/gmail-mcp/    read-only Gmail MCP server powering /inbox (gmail.readonly)
eval/               the LLM-judge evaluation harness (DESIGN, experiments, scorer)
data/               tracker schema + FICTIONAL sample CSVs (*.sample.csv) + sample threads
resume/             Resume-Facts.sample.md, voice.sample.md, a compiled sample resume
companies/example/  a sample per-target working folder
CLAUDE.md           the orchestration layer (role, phrasing dials, honesty boundary)
```

The `*.sample.*` files and `companies/example/` are a fictional dataset so the repo reads end-to-end. Real applications, contacts, resumes, and notes are private and never committed.

---

## Notes
- **Read-only on email; draft-only on outreach.** The Gmail integration can only read, and `/inbox` and `/outreach` produce text and log the touch. A human presses send.
- **Nothing writes to the tracker or a resume without approval.** The skills propose; I confirm.
- **The eval harness is designed, not yet run** (`eval/results/` is empty). Running experiment E1 (deep vs light) is the next step.

Built by Jeffrey Zhu. MIT licensed.
