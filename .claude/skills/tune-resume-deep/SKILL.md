---
name: tune-resume-deep
description: Deep, multi-agent resume tune for dream / high-value companies. Use when the user pastes a specific job posting and wants the heavier, thoroughly-optimized tune (not the fast one-pass `tune-resume`). Generates several strategically distinct full drafts, autonomously judges them via a pairwise tournament + critic panel, runs a shallow refine loop on the winner, then holds an interactive final review with the user; on approval, writes the tuned resume into `companies/<name>/` and logs the application to `data/applications.csv`.
---

# Deep-Tune Resume to a Job Description

Act as a tech-recruiting expert running a **deep, high-effort tune** of Jeffrey Zhu's resume for a company he really values. This trades latency for quality: explore widely, judge thoroughly, then converge. It is NOT the fast path — for volume applications use the light `tune-resume` skill instead.

**Reserve this for the handful of dream / high-priority targets.** If the user wants a quick tune, redirect them to `/tune-resume`.

## Core principles (read before running)
- **Buy breadth, not depth.** Spend the effort budget *horizontally* — more diverse candidate drafts, more independent judges, pairwise comparison — not on longer refine chains. Deep iteration over-fits to the JD's wording and reads as pandering. Refine is capped at 2-3 passes.
- **Grounding, not honesty-policing.** The tuner draws its material only from `Resume-Facts.md` (CAN CLAIM) so it builds from real content and never invents experiences. There is **no in-loop honesty veto and no honest-gap report** — Jeffrey owns the honesty call at the interactive review at the end. Still: never silently fabricate; surface anything uncertain for him to approve at review time.
- **Deterministic checks do the mechanical work; agents do the judgment.** Page count, ATS-parse safety, keyword presence, and AI-tell blocklist are checked with scripts/grep. Agent critics evaluate ONLY what a script can't: recruiter-scan impact, hiring-manager credibility, narrative coherence, and over-fit/pandering.
- **Hold the phrasing dials** (from `CLAUDE.md`): technical but legible to a non-engineer recruiter; human (no buzzword tells — no "leveraged/spearheaded/robust/seamless", no formulaic parallelism, no dash-as-connector); tight (result + so-what, no padding).

## Inputs
- The **job description** — pasted or a URL/file. If none provided, ask before doing anything.
- `resume/resume-ai.tex` / `resume/resume-mlds.tex` — the two base variants (source of truth for what's on the page).
- `resume/Resume-Facts.md` — truthful inventory; the tuner's ONLY source for claims (CAN CLAIM section).
- `CLAUDE.md` — positioning priority and phrasing dials.

Read all of these before starting. Use the scratchpad directory for all intermediate drafts; the final files land in `companies/<name>/` (see step 6).

## Procedure

### 0. Sync resume-fact sources first (auto-gated, cheap)
A hook has already refreshed all configured ground-truth sources (`assets/sources.txt` — UCSF research notes + watched GitHub project repos) and written a change flag. Read `assets/.sources-status`:
- `unchanged` or missing -> skip this step, go to 1. (Common case: no cost, no prompt.)
- `changed: <sources>` -> those sources have new material since `Resume-Facts.md` was last synced. Tell Jeffrey which changed and reconcile before tuning (default yes; if he skips, proceed on current facts). Reconcile by running the `sync-facts` procedure for the named sources: refresh + read each (a `gdoc` from its local PDF; a `github` repo from its committed README/results at HEAD), propose a tight diff of new/changed **claimable** facts (metrics, methods, statistical results, dataset scale) as suggestions only — the honesty boundary is Jeffrey's; write only approved lines into `resume/Resume-Facts.md` (CAN CLAIM, matching its style); then stamp each reconciled source (`sha256sum "<local-pdf>" | cut -d' ' -f1 > assets/.src-<name>.hash` for a gdoc, `bash .claude/hooks/gh-claim-hash.sh <owner/repo> > assets/.src-<name>.hash` for a github repo). Do not write `assets/.sources-status` (the hook owns it). Then continue.
- `new: <files>` -> undeclared files have appeared in `assets/` and likely carry new claimable material. Offer to review them (default yes): run the `sync-facts` procedure on each new file — read it, propose claimable-fact suggestions (metrics, methods, results; Jeffrey's honesty call), write only approved lines into `resume/Resume-Facts.md`, then mark it seen (append its path to `assets/.seen-assets`) and, if it's a recurring source, declare it in `assets/sources.txt`. Do not write `assets/.sources-status`. (`changed:` and `new:` can both appear — handle both.)
- `error: <sources>` -> the hook couldn't verify those sources (network/auth). Tell Jeffrey their facts may be stale, but do NOT block — continue.

### 1. Setup + checklist
- Classify the JD and pick the closer base variant (AI vs ML/DS); note the call. If the JD is a poor fit for both (pure frontend / generalist SWE), say so rather than forcing a deep tune.
- Extract the JD's must-have skills, tools, and role keywords in the JD's own wording.
- Build a **checklist** from `JD ∩ Resume-Facts`:
  - **Hard gates (pass/fail, checked by script):** one page; ATS-parse-safe; ASCII-only (no en/em-dash, no math arrows); job title exactly `Software Engineer Intern - AI Agents`; AI-tell blocklist clean.
  - **Coverage (present/absent, necessary-condition — do NOT maximize):** which JD must-haves Jeffrey truthfully has appear on the page.
  - Note which JD keywords have no truthful backing — these are candidates to raise at review, not to invent.
  - **Relevant Coursework line - default OFF.** Jeffrey's experience and projects already demonstrate stats/ML depth more convincingly than any course title, so on most tunes a coursework line is low-density and redundant. Include it only for **academic / quant / research-heavy** targets (quant firms, research-engineer/scientist roles, JDs that name foundational theory or specific courses), where reviewers and ATS look for named coursework. When included: pull from the high-value set in `Resume-Facts` (Stat 154 Statistical ML, Stat 134 Probability, Stat 135 Mathematical Statistics, Math 128A Numerical Analysis, Math 54 Linear Algebra), readable titles, one line. Never claim a Statistics major/minor - Jeffrey is a single Data Science major; the individual courses are the honest vehicle for that background.

### 2. Wide diverge (parallel subagents)
Spawn **4-6 subagents in parallel**, each producing a *full* tuned draft from the chosen base variant, drawing only from `Resume-Facts`. Assign each a **distinct, specified angle** so diversity is real, not cosmetic — e.g.:
- lead with **agentic / LLM-systems engineering**
- lead with **ML / research depth**
- lead with **impact / scale / metrics**
- **maximize truthful JD-keyword alignment**
- (add angles as the JD warrants)

Each draft must independently pass the hard gates.

Each draft should also **pick which project(s) to feature by JD fit from the full confirmed pool in `Resume-Facts` (CAN CLAIM), not just the one the base variant prints** — a draft may swap in a confirmed project the base `.tex` omits when it's a stronger fit or fills a gap the shown one doesn't (it's confirmed, so use it freely). Keep experience above projects and hold one page: swap/add only when space allows, never by cutting a stronger experience bullet. (E.g. a regression-heavy JD should feature the regression project even if the base lists only a classification one.)

### 3. Autonomous thorough judging (tournament + panel)
Judge the drafts thoroughly and pick the winner **without asking the user**:
- Run a **pairwise comparison tournament** (round-robin or bracket) — LLMs judge "A vs B, which is stronger for this JD?" far more reliably than absolute scores. **Do not assign numeric quality scores.**
- Judge on: recruiter 6-second-scan impact, hiring-manager technical credibility, narrative coherence, and JD-fit — with the checklist as a gate.
- Select the single strongest **whole** draft (coherence matters — do not Frankenstein bullets across drafts here). Keep the best ideas from runner-up drafts as **notes** for the editor in step 4.

### 4. Shallow refine loop (2-3 passes, hard cap)
On the winning draft only:
- **Critic panel** (parallel): recruiter-scan, hiring-manager credibility, narrative coherence, and an explicit **over-fit / pandering guard** ("does this still read as a strong general resume, or has it become JD-mirroring?").
- **Editor** integrates the critiques *and* the runner-up ideas from step 3 coherently (this is where good ideas from other drafts get woven in, by judgment — not copy-paste).
- **Tuner** applies the edits; re-run hard gates.
- Stop when hard gates pass, critics raise no new material issues, and edits go cosmetic. **Never exceed 3 passes** — past that is over-fitting.

### 5. Interactive final review (with Jeffrey)
Present, and **wait for his response** — do not finalize yet:
- The tuned resume (rendered) and a **diff against the base variant** so he sees exactly what changed from his known-good resume.
- Which base variant and angle won, and why.
- The JD keywords surfaced and where they landed.
- **Anything uncertain** — JD-relevant skills or accomplishments he plausibly has but that aren't confirmed in `Resume-Facts` — surfaced as questions for him to confirm or reject. This is his honesty-control point.
- Iterate on his feedback (edits, additions he confirms, cuts) until he says it's good. Add confirmed items to `resume/Resume-Facts.md`.

### 6. Output on approval — into the company folder
Only once Jeffrey says it's good. Dream targets are archived per-company (NOT the rolling root `resume.pdf`, which is for volume tunes):
- Pick a company **slug** (lowercase, hyphenated, e.g. `tiktok`; if a company has multiple dream roles, `tiktok-mle`). Create `companies/<slug>/` if it doesn't exist.
- Save the JD there as `companies/<slug>/jd.md`.
- Compile the approved source and emit it as **`companies/<slug>/resume.pdf`** (keep the source as `companies/<slug>/resume.tex`).
- `pdflatex -interaction=nonstopmode -halt-on-error resume.tex` (run in the folder) — fix any error and recompile.
- **Verify one page:** log says `Output written on ... (1 page`. If it spilled to 2, cut the lowest-value bullet/keyword and recompile.
- **Extraction sanity check:** `pdftotext companies/<slug>/resume.pdf out.txt`; confirm dates, job title, and key metrics extract as clean ASCII (no stray bytes, no merged numbers).
- Remove `.aux/.log/.out` and the temp `.txt`, and any intermediate drafts from the scratchpad.
- Give a suggested submission filename, e.g. `Jeffrey-Zhu-<Role>-Resume.pdf`.

### 7. Log to the tracker
After `resume.pdf` is emitted, append one row to `data/applications.csv`:
- **Read `data/SCHEMA.md` first** and use only its controlled enum values.
- Confirm the row's fields with Jeffrey during the interactive review (step 5) — company, role, team, location, req URL, priority. **Default assumption: he's applying right now, right off this tune**, so log `status = applied` with today's `date_applied` without asking. Only ask a single either/or if you have reason to think otherwise ("applying now, or is this one for later?"); use `status = to_apply` with a `next_action` / `next_action_date` only if he says later.
- Fields: next free `app_id`; `source` (usually `cold` or `referral`); `resume_variant` = the base that won (`ai`/`mlds`, or `custom`); `contact_id` if a recruiter/referrer is linked (else blank); `notes` for anything useful. Quote any field containing a comma.
- Confirm the appended row back to Jeffrey (its `app_id` and key fields).

## ATS-safe formatting (verified, non-negotiable)
- ASCII hyphen `-` only. **No** en/em-dashes (`--`, `—`) — this template extracts them as an invisible soft-hyphen (byte 0xAD).
- **No** math arrows (`$\rightarrow$`) — they extract as nothing; write "to".
- Keep `\renewcommand{\labelitemi}{\textbullet}`, standard section headings, single column, plain-text grouped skills.
- Job title stays exactly **`Software Engineer Intern - AI Agents`** (must match LinkedIn).

## Guardrails
- **Reserve for dream targets.** Redirect quick tunes to `/tune-resume`.
- **Breadth over depth** — never exceed 3 refine passes; spend budget on more drafts/judges instead.
- **Whole-draft selection** in step 3 (coherence); idea-grafting happens only in the editor step, by judgment.
- **No fabrication.** Build from `Resume-Facts` (CAN CLAIM); surface uncertain items at the interactive review; nothing unconfirmed reaches the page without Jeffrey's OK.
- **No numeric quality scores** — selection is pairwise/comparative.
- **`companies/<slug>/resume.pdf` is emitted only after Jeffrey approves at review**, and the `applications.csv` row is logged only after export.
