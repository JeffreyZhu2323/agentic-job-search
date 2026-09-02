---
name: tune-resume
description: Produce a job-description-tailored version of Jeffrey Zhu's resume (fast, single-pass; use for volume applications). Use when the user pastes (or points to) a specific job posting and wants a resume tuned for it. Picks the closer base variant (AI vs ML/DS), surfaces the JD's keywords from truthful content only, builds a one-page ATS-safe draft, holds an interactive review, then exports `resume.pdf` and holds a second post-export approval gate; on that approval it logs the application to `data/applications.csv` and archives the submitted resume (pdf + tex) to the flat store `data/resumes/` for every application; for `dream`/`high`-priority roles it additionally creates a `companies/<name>/` workspace (JD + fit-notes + a resume copy).
---

# Tune Resume to a Job Description

Act as a tech-recruiting expert tailoring Jeffrey Zhu's resume to a specific job description (JD). The goal is a **light-touch, honest, ATS-optimized tune** — keyword surfacing and reordering, never a rewrite and never fabrication.

## Inputs
- The **job description** — pasted by the user or a URL/file they point to. If none was provided, ask for it before doing anything.
- Base resumes (source of truth for what's on the page), in `resume/`:
  - `resume/resume-ai.tex` — AI / LLM Engineer variant
  - `resume/resume-mlds.tex` — ML Engineer / Data Scientist variant
- `resume/Resume-Facts.md` — the full truthful inventory of what Jeffrey **can** and **cannot** claim. **Never put anything on the resume that isn't in its CAN CLAIM section.**
- `CLAUDE.md` — positioning priority and the phrasing dials.

## Procedure
0. **Sync resume-fact sources first (auto-gated, cheap).** A hook has already refreshed all configured ground-truth sources (`assets/sources.txt` — UCSF research notes + watched GitHub project repos) and written a change flag. Read `assets/.sources-status`:
   - `unchanged` or missing -> skip this step, go to 1. (This is the common case: no cost, no prompt.)
   - `changed: <sources>` -> those sources have new material since `Resume-Facts.md` was last synced. Tell Jeffrey which changed and reconcile before tuning (default yes; if he skips, proceed on current facts). Reconcile by running the `sync-facts` procedure for the named sources: refresh + read each (a `gdoc` from its local PDF; a `github` repo from its committed README/results at HEAD), propose a tight diff of new/changed **claimable** facts (metrics, methods, statistical results, dataset scale) as suggestions only — the honesty boundary is Jeffrey's; write only approved lines into `resume/Resume-Facts.md` (CAN CLAIM section, matching its style); then stamp each reconciled source so it won't re-prompt (`sha256sum "<local-pdf>" | cut -d' ' -f1 > assets/.src-<name>.hash` for a gdoc, `bash .claude/hooks/gh-claim-hash.sh <owner/repo> > assets/.src-<name>.hash` for a github repo). Do not write `assets/.sources-status` (the hook owns it). Then continue with the current facts.
   - `new: <files>` -> undeclared files have appeared in `assets/` and likely carry new claimable material. Offer to review them (default yes): run the `sync-facts` procedure on each new file — read it, propose claimable-fact suggestions (metrics, methods, results; Jeffrey's honesty call), write only approved lines into `resume/Resume-Facts.md`, then mark it seen (append its path to `assets/.seen-assets`) and, if it's a recurring source, declare it in `assets/sources.txt`. Do not write `assets/.sources-status`. (`changed:` and `new:` can both appear — handle both.)
   - `error: <sources>` -> the hook couldn't verify those sources (network/auth). Tell Jeffrey their facts may be stale, but do NOT block — continue.
1. **Read** both base `.tex` files (in `resume/`), `resume/Resume-Facts.md`, and `CLAUDE.md`.
2. **Classify the JD** and pick the closer base variant:
   - AI Engineer / Applied AI / LLM / agents / GenAI → start from `resume-ai.tex`.
   - ML Engineer / Data Scientist / Research Engineer / modeling / stats → start from `resume-mlds.tex`.
   - Mixed → pick the dominant framing and note the call. If the JD is a poor fit for both (e.g., pure frontend or generalist SWE), say so rather than forcing a tune.
3. **Extract the JD's requirements** — list its must-have skills, tools, and role keywords in the JD's own wording.
4. **Map JD → truthful content** (this is the whole job):
   - For each JD keyword Jeffrey genuinely has (per Resume-Facts), make sure it appears, using the JD's exact term where truthful (JD says "LLM evals" → mirror that phrasing).
   - Reorder bullets so the most JD-relevant experience leads.
   - Reorder/relabel the skills lines so the JD-relevant cluster is first.
   - Adjust the tagline to the JD's role token if truthful.
   - **Pick which project(s) to feature by JD fit from the full confirmed pool in `Resume-Facts` (CAN CLAIM), not just the one the base variant prints.** As part of this mapping, review every confirmed project and feature the best JD match(es) - swapping in one the base `.tex` omits when it's a stronger fit or fills a gap the shown one doesn't (it's confirmed, so use it freely, no ask). Keep experience above projects and hold one page: only swap/add when space allows, never by cutting a stronger experience bullet. E.g. a regression-heavy JD should feature the regression project even if the base lists only a classification one.
   - **Relevant Coursework line - default OFF.** Jeffrey's experience and projects already demonstrate stats/ML depth more convincingly than any course title, so on most tunes a coursework line is low-density and redundant. Include it only for **academic / quant / research-heavy** targets (quant firms, research-engineer/scientist roles, JDs that name foundational theory or specific courses), where reviewers and ATS look for named coursework. When included: pull from the high-value set in `Resume-Facts` (Stat 154 Statistical ML, Stat 134 Probability, Stat 135 Mathematical Statistics, Math 128A Numerical Analysis, Math 54 Linear Algebra), readable titles, one line. Never claim a Statistics major/minor - Jeffrey is a single Data Science major; the individual courses are the honest vehicle for that background.
5. **For anything NEW or uncertain — surface and ask, never invent, never silently drop.** This applies equally to skills and to experience/accomplishments:
   - Use freely whatever is confirmed in Resume-Facts (CAN CLAIM) — skills and the real bullet facts. Reword and reorder confirmed content as needed.
   - If you think of anything that would strengthen the resume for this JD but you don't know or aren't sure Jeffrey has it / did it — whether a **skill/tool** OR an **accomplishment, detail, or metric** in one of his internships, research, or projects — **never invent it silently.** Do not put it on the resume; surface it in the closing questions (step 9) and let Jeffrey confirm.
   - Only after he confirms does it go in (a skill as a keyword; an accomplishment written into a bullet).
   - Items in DOES NOT HAVE are confirmed false — leave them off; flag one only if it's a central JD requirement.
6. **Hold the phrasing dials** (from CLAUDE.md): technical but legible to a non-engineer recruiter, human (no buzzword tells — no "leveraged/spearheaded/robust/seamless", no formulaic parallelism), tight (result + so-what, no padding).
7. **Keep ATS-safe formatting** (these are verified, non-negotiable):
   - ASCII hyphen `-` only. **No** en/em-dashes (`--`, `—`) — with this template they extract as an invisible soft-hyphen (byte 0xAD).
   - **No** math arrows (`$\rightarrow$`) — they extract as nothing; write "to".
   - Keep `\renewcommand{\labelitemi}{\textbullet}`, standard section headings, single column, plain-text grouped skills.
   - Job title stays exactly **"Software Engineer Intern - AI Agents"** (must match LinkedIn).
8. **Build a working draft and compile (hold the final export):**
   - Write the tuned source to a working `.tex` (use the scratchpad; don't emit `resume.pdf` yet).
   - `pdflatex -interaction=nonstopmode -halt-on-error <file>.tex` — fix any error and recompile.
   - **Verify one page:** confirm the log says `Output written on ... (1 page`. If it spilled to 2, cut the lowest-value bullet/keyword and recompile.
   - **Extraction sanity check:** `pdftotext <file>.pdf out.txt` and confirm dates, the job title, and key metrics come out as clean ASCII (no stray bytes, no merged numbers).
9. **Interactive final review with Jeffrey** — present the draft and **wait for his response; do not finalize yet:**
   - **Base this review on a mechanical diff, not memory.** Run `diff resume/<base-variant>.tex <working>.tex` (the exact base variant you started from in step 2) to get the complete, deterministic list of every changed line, and walk Jeffrey through every one. This is a hard guarantee that no edit reaches the resume unmentioned; a self-reported summary is not. Drop only pure-cosmetic lines (comments, whitespace, the variant header) from the walkthrough, **never** a content change. You are surfacing the changes for Jeffrey to judge, not judging honesty for him.
   - Which base variant you started from and why.
   - The JD keywords you surfaced and where you put them.
   - **Two question lists for Jeffrey to confirm** (this is how nothing good gets missed just because the skill didn't know about it):
     - *Skills to confirm* — every JD-relevant skill/tool you're unsure he has: "The JD wants X — do you have experience with this? I'll add it if so."
     - *Accomplishments to surface* — JD-relevant things he plausibly did in an internship/research role that would strengthen this application but aren't on the resume: "This JD values Y — did you do anything like Y at PANW / UCSF / PreciX? If so I'll write it into a bullet."
   - Anything in DOES NOT HAVE that's a **core** JD requirement, flagged plainly (left off, not fabricated).
   - Also confirm the **tracker fields** for step 12 — company, role, team, location, req URL, priority. **Default assumption: he's applying right now, right off this tune** (the common case), so plan to log `status = applied` with today's date without asking. Only ask a single either/or if you have reason to think otherwise: "applying now, or is this one for later?" — and use `to_apply` only if he says later.
   - Iterate on his feedback (edits, confirmed additions, cuts) until he says it's good. Add whatever he confirms to `resume/Resume-Facts.md`.
10. **On review approval — export `resume.pdf`:**
   - Compile the approved source and emit it as **`resume.pdf`** in the Career root (keep the source as `resume.tex`).
   - Re-verify one page and re-run the extraction sanity check on `resume.pdf`.
   - Remove `.aux/.log/.out` and the temp `.txt`, and the working draft from the scratchpad.
   - Give a suggested submission filename, e.g. `Jeffrey-Zhu-<Role>-Resume.pdf`.
11. **Post-export gate — present the exported PDF and WAIT for Jeffrey's approval before committing anything downstream.** The step 9 review only shows a summary of the changes; this is Jeffrey's first look at the fully rendered `resume.pdf`. Tell him it's ready to open, and do **not** proceed to archiving or logging until he approves. If he wants changes, loop back: edit the source, re-export (step 10), and re-present. Only an explicit OK here unlocks step 12.
12. **On post-export approval — archive the submitted resume, then log the tracker:**
   - **Universal resume archive (every application, all priorities):** copy the exported `resume.pdf` and its `resume.tex` into the flat store `data/resumes/`, named by tracker key `<app_id>-<company-slug>-<resume_variant>` — e.g. `data/resumes/APP-014-arm-ai.pdf` (and `.tex`). This is the complete, permanent record of exactly what you sent, keyed to `applications.csv`; a submitted resume is frozen, so never edit it after. Determine the `app_id` (next free, from the log step below) and a lowercase-hyphenated company slug first, then write both files.
   - **Companies workspace folder — additionally, only if `priority` is `dream` or `high`:** create `companies/<name>/` and write `jd.md` (the full JD plus a short fit-notes block: strong matches, honest gaps left off, interview talking points), then copy the exported `resume.pdf` and its `resume.tex` into it too, so the priority workspace stays self-contained for interview prep (this duplicates the flat-store record, which is fine — a submitted resume never changes). **Skip the folder for `mid` / `insurance`** — volume apps get the `data/resumes/` archive above plus a tracker row, no workspace folder (per `CLAUDE.md`: only priority pursuits get a folder).
   - **Log to `data/applications.csv`:** **read `data/SCHEMA.md` first** and use only its controlled enum values. If a row for this role already exists (e.g. one created earlier from outreach), update it in place rather than duplicating. Otherwise use the fields confirmed in step 9: next free `app_id`; `company`, `role_title`, `team`, `location`, `req_url`, `priority`; `source` (usually `cold` or `referral`); `resume_variant` = the base you used (`ai`/`mlds`, or `custom`); `status` = `applied` with today's `date_applied` by default (assume he's applying right off this tune); use `to_apply` with a `next_action` / `next_action_date` only if he said this one is for later; `contact_id` if a recruiter/referrer is linked (else blank); `notes` as useful (reference the archived resume: `data/resumes/<app_id>-<slug>-<variant>.pdf`, plus `companies/<name>/resume.pdf` for priority pursuits). Quote any field containing a comma.
   - Confirm the row (its `app_id` and key fields), the archived resume path in `data/resumes/`, and any companies folder created back to Jeffrey.

## Guardrails
- **Never add anything uncertain without asking — skills and experience alike.** Whatever is confirmed (Resume-Facts CAN CLAIM) you use freely. For **anything new or uncertain** — a skill/tool, or an accomplishment/detail/metric in an internship, research, or project — never invent it silently and never silently drop it; surface it in the closing questions and add it only once Jeffrey confirms. Confirmed content can be reworded/reordered, but nothing unconfirmed goes on the page without asking.
- **Always end by asking** about everything new/uncertain (uncertain skills + possible unshown accomplishments) so nothing good is missed just because the skill didn't know Jeffrey had it or did it.
- **Light tune, not a rewrite:** surface keywords and reorder; keep the base bullets' facts and metrics intact.
- If surfacing a real-but-unshown accomplishment would help, don't invent it — ask Jeffrey (step 9) for the details so it can be shown truthfully in a bullet.
