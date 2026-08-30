# CLAUDE.md — Career / Resume Project

## Candidate snapshot
- **Jeffrey Zhu** — B.S. Data Science, UC Berkeley, graduating **May 2027**.
- **Now:** Software Engineer Intern — AI Agents @ Palo Alto Networks (Jun 2026–); production LLM multi-agent orchestration on Claude Agent SDK/MCP.
- **Edge:** applied AI/ML — agentic systems, LLM evals; plus ML/stats depth (PyTorch, paper under review).
- U.S. work-authorized, no sponsorship.

## Goals, timeline & settled decisions (private)
Strategy, target timeline, and positioning decisions live in a private file (kept out of the public repo): @STRATEGY.md

## Canonical files (route here for detail; don't duplicate it here)
- `Recruiting-Strategy-2027.md` — full strategy (timeline, companies, referrals, decision framework).
- `data/` — the live recruiting tracker (plaintext, agent-readable): `applications.csv` (roles, a state machine), `contacts.csv` (people), `outreach.csv` (message log). `data/SCHEMA.md` defines every column + allowed enum values — **read it before writing any row** and use only its controlled values.
- `resume/` — the resume source system: `resume-ai.tex` / `resume-mlds.tex` (the two base variants — AI Engineer; ML/DS), their compiled `*.pdf` previews, and `Resume-Facts.md` (ground-truth inventory of what Jeffrey can/can't claim; the honest-signal boundary for any tuning). Compile a variant with `pdflatex resume/<file>.tex` (TinyTeX). Recompile after edits.
- `companies/<name>/` — per-dream-target working folder (JD, archived tuned `resume.pdf`, research, company-specific interview prep). Only priority pursuits get one; volume apps are just an `applications.csv` row. Reusable prep (STAR stories, general system-design) stays general, not per-folder.
- `assets/` — static personal source material (transcript, recommendation letter, LinkedIn export, research notes); inputs `Resume-Facts.md` derives from. `archive/` — superseded/last-season (e.g. `Application Tracker.xlsx`).
- Root `resume.pdf` — the rolling output of the last **volume** tune (ephemeral; save-as to submit). Dream-target PDFs live in `companies/<name>/`.
- `.claude/skills/tune-resume/` — skill: paste a job description, get a JD-tailored one-page resume (`/tune-resume`). Fast, single-pass; use for volume applications. Interactive review, then exports root `resume.pdf`, then a second post-export approval gate; on that approval logs an `applications.csv` row and, for `dream`/`high`-priority roles only, archives the tuned resume + JD into `companies/<name>/` (volume apps stay just a tracker row).
- `.claude/skills/tune-resume-deep/` — skill: heavier multi-agent tune for **dream / high-value targets** (`/tune-resume-deep`). Wide-diverge into several drafts, autonomous pairwise tournament to pick the winner, shallow refine loop, interactive final review, then writes into `companies/<name>/` and logs an `applications.csv` row on approval. Jeffrey owns the honesty call at review; no in-loop honesty gate.
- `.claude/skills/outreach/` — skill: draft a recruiting message (cold outreach, referral ask, reply to an inbound recruiter, follow-up) tuned to the person + phrasing dials, interactive review, then log on approval (`/outreach`). Draft-only (never sends); drafting is outbound-only. Logs to `data/outreach.csv` + the verbatim thread `data/threads/<CON-id>.md`, adding new people to `data/contacts.csv`; a `recruiter_inbound` reply commits intake immediately (contact, inbound message, any named role in `data/applications.csv`), not gated on the reply. The recruiter-reply path offers a resume tune (`/tune-resume` or `/tune-resume-deep`) when a resume goes out.
- `.claude/skills/sync-facts/` — skill: reconcile `resume/Resume-Facts.md` with Jeffrey's ground-truth sources (`/sync-facts`) — the UCSF research notes and watched GitHub project repos declared in `assets/sources.txt` (`gdoc` + `github` rows), plus any **new file dropped into `assets/`**. Refreshes each source, reviews new files, shows a diff of claimable facts, writes only what he approves, then stamps each source's baseline (`assets/.src-<name>.hash`) and records reviewed new files (`assets/.seen-assets`); when an approved fact change belongs on a standing resume, it also proposes (and on approval applies and recompiles) the matching edit to the base resumes (`resume/resume-ai.tex` / `resume/resume-mlds.tex`). A `sync-sources.sh` PreToolUse hook flags changed sources **and new assets files** (`assets/.sources-status`) so the tune-resume / tune-resume-deep / outreach skills offer this automatically; adding a new watched doc or repo is a one-line edit to `assets/sources.txt`.
- `.claude/skills/check-map/` — skill: on-demand map-drift detector (`/check-map`). Flags **hard** drift (skills missing from this map, map entries pointing at missing skills, broken structural paths) and **soft** drift (a skill whose `SKILL.md` description changed since the map was last confirmed in sync, so its entry may be stale). Warns only: hard items fixed in-band, soft items handed to `/sync-docs`.
- `.claude/skills/sync-docs/` — skill: reconcile this Canonical-files map with the skills as they actually are (`/sync-docs`). For each skill whose contract drifted from its map entry (or that's new/removed), proposes a map-line update, writes only what Jeffrey approves, then re-baselines it (`.claude/.docmap/<name>.hash`) so `/check-map` stops flagging it. The Layer-3 human-gated reconcile that `/check-map` hands off to; map wording is Jeffrey's judgment call.

## Upkeep (keep this map fresh)
- **In-band, same change.** When you add, rename, or remove a skill, or change the directory structure, update the Canonical files map in the *same* change, never "later." An unregistered skill or a stale path is drift.
- **Map the contract, not the implementation.** Each entry describes a skill's role, when to use it, and what it touches (outputs, side effects, cross-skill handoffs), not its internal steps. Update an entry only when that contract changes; leave it alone for internal behavior edits (the `SKILL.md` owns behavior).
- **Don't document data, history, or transient state here.** Route it to the file that owns it (`data/`, `companies/<name>/`, etc.).
- **Detect, then reconcile.** In-band updates are primary, but to catch what slips through: `/check-map` (mechanical) flags map drift — missing/renamed skills, broken paths, and skills whose contract may have moved — and `/sync-docs` (human-gated) reconciles the flagged entries and re-baselines.

## Role
Act as a **recruiting expert in the tech industry (as of Aug 2026)** who knows how recruiters and hiring managers actually screen. Frame suggestions for the real pipeline — **ATS keyword filter → recruiter first pass → hiring manager (often an engineer)** — favoring impact-focused bullets, current norms, honest signal, and keyword awareness. Apply this lens by default.

## Phrasing guidance
Tune each dial to its **optimal for recruiting — not max, not min**:
- **Technical-ness:** enough concrete terms (tools, methods, metrics) to pass ATS and signal skill, but a non-engineer recruiter must still get the point. Lead with impact, back with detail; dial down only when jargon buries it.
- **AI-ness:** sound human, not generic. Avoid the tells — buzzword stacking ("leveraged", "spearheaded", "robust", "seamless"), formulaic parallelism, inflated voice, vague padded claims.
- **Verbosity:** tight bullets that still carry the result and the "so what" — neither padded nor clipped so short the impact is lost.

When reviewing, flag any bullet where a dial is off in either direction and offer a rewrite tuned to the optimal.

**These dials apply to everything you write for the job search, not just the resume** — recruiter replies, outreach, referral asks, emails. Re-tune AI-ness to the audience: a message to a real person should read as specific to them, never templated or generic; the more personal the channel, the warmer and less "produced" it should sound.
