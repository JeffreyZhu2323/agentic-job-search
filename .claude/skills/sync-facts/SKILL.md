---
name: sync-facts
description: Reconcile resume/Resume-Facts.md with Jeffrey's ground-truth sources (UCSF research notes + watched GitHub project repos in assets/sources.txt) and with any new file that appears in assets/. Refreshes each source, reviews new files, shows a diff of claimable facts, and writes only what Jeffrey approves. Run after a research or project session, or when a new source doc lands; the resume and outreach skills also offer it automatically when the hook detects a changed source or a new assets file.
---

# Sync Resume-Facts from ground-truth sources

Reconcile `resume/Resume-Facts.md` against Jeffrey's live ground-truth sources and any newly-added source material. This is the deliberate, human-approved update of the honesty boundary: you surface what the sources now support, Jeffrey decides what actually goes in. This is the intended primary way to keep the facts current — run it after a research session, after pushing project work, or after dropping a new document into `assets/`. (The tune-resume / tune-resume-deep / outreach skills run the same reconcile automatically, but only as a safety net when the hook detects a changed source or a new file.)

## What gets reconciled
**1. Declared sources** — `assets/sources.txt` (pipe-delimited: `type | name | id | localfile`). Two types:
- **`gdoc`** — a Google Doc (e.g. UCSF research notes). `id` is the doc ID; `localfile` is the local PDF it exports to. Claimable content: metrics, statistical results (tests, effect sizes, significance), dataset/cohort scale.
- **`github`** — a project repo (e.g. `ml-projects`). `id` is `owner/repo`. Claimable content: model performance metrics, methods, tech stack, dataset scale — usually in the README and committed results files (`results/*.json`, etc.).

Each declared source has a baseline hash at `assets/.src-<name>.hash` recording its state as of the last sync.

**2. New files in `assets/`** — any file that appears in `assets/` that isn't a hidden state file, `sources.txt`, or an already-declared source `localfile`. A new file (a research paper, a transcript, an offer letter, a fresh notes export) probably carries new claimable material. Reviewed new files are recorded in `assets/.seen-assets` (one relative path per line) so they stop being flagged.

**This skill writes the baselines and the seen-list; it never writes `assets/.sources-status`** (the `sync-sources.sh` hook owns the status, and always refreshes it before any consumer reads it).

## Procedure
1. **Determine what to reconcile.** Read `CLAUDE.md` (for the phrasing dials) and `assets/sources.txt`, then:
   - Run **directly** (`/sync-facts`): self-check everything — for each declared source, refresh + hash + compare to its baseline (reconcile the ones that differ or have no baseline); and scan `assets/` for new files (not hidden, not `sources.txt`, not a declared `localfile`, not in `.seen-assets`). Do not trust `.sources-status` here (the hook doesn't fire for this skill).
   - Invoked **from another skill** for named sources / files (from a `changed:` or `new:` status line): reconcile just those.
2. **Refresh + read each item to reconcile:**
   - **`gdoc` source:** refresh the local PDF from the live doc (overwrites in place), then read it:
     ```
     curl -sfL "https://docs.google.com/document/d/<id>/export?format=pdf" -o "<localfile>"
     ```
     If the fetch fails (offline/permissions), report it and skip that source — do not proceed on a stale or half-written PDF.
   - **`github` source:** read the repo's claim-bearing files **at current HEAD**. Prefer a fresh local clone if one exists (e.g. `ml-projects` at `C:/Users/jeffr/Desktop/ml-projects`) — `git -C <clone> pull --ff-only` first so you're reading HEAD, not a stale checkout; otherwise pull file contents via `gh api`. Read the README(s) and the committed results/metrics files.
   - **New file:** read it in place (`assets/<name>`). Extract what's genuinely claimable (metrics, methods, results, dataset scale, credentials).
   - Also read `resume/Resume-Facts.md`.
3. **Propose a diff — suggestions only.** Per item, present:
   - **Add** — claimable facts in the source/file not yet reflected in Resume-Facts.
   - **Update** — existing facts whose numbers changed (a re-run notebook, new results file, revised stat table).
   - **Flag** — anything ambiguous, not clearly claimable, or hard to read. Surface it; do not assume.
   Frame each as "worth claiming, and stated this way?" This is the honesty call and it is Jeffrey's. Keep entries honest, specific, and in the phrasing dials.
4. **Write on approval.** Put only the lines Jeffrey approves into `resume/Resume-Facts.md` (CAN CLAIM section), reworded to match the file's existing style. Nothing unreviewed goes in.
5. **Record what you reconciled** so the hook stops flagging it. Use the same computation the hook uses (so values match by construction):
   - **`gdoc` source:** `sha256sum "<localfile>" | cut -d' ' -f1 > assets/.src-<name>.hash`
   - **`github` source:** `bash .claude/hooks/gh-claim-hash.sh <owner/repo> > assets/.src-<name>.hash`
   - **New file:** decide with Jeffrey which it is, then:
     - **Recurring source** (a live doc or repo that will keep changing) — add a row to `assets/sources.txt` (`gdoc` with a `localfile`, or `github`) and baseline it as above. Being a declared `localfile` excludes it from future novelty scans; no seen-entry needed.
     - **Static one-off or not claimable** (a fixed PDF, a reference doc, nothing to claim) — append its path to `assets/.seen-assets` (`echo "assets/<name>" >> assets/.seen-assets`). It won't meaningfully change, so it just needs to stop flagging.
   Do **not** write `assets/.sources-status` — leave that to the hook (writing it here would mask anything you didn't reconcile this run).
6. **Confirm** to Jeffrey exactly what was added/updated per item, which new files were declared vs marked seen, and anything left flagged for later.

## Guardrails
- **Honesty boundary — nothing enters `Resume-Facts.md` without Jeffrey's explicit approval.** Surface and suggest; never auto-write an unreviewed claim.
- **`gdoc` notes are image-heavy stat tables.** Read the numbers carefully; if a value is unclear from a screenshot, flag it rather than guessing.
- **`github` metrics can change silently.** A re-run notebook or updated results file shifts a number with no other signal; read the committed metric files carefully and diff against what's in Resume-Facts, don't assume the old number still holds.
- **Every reviewed new file gets resolved** — declared as a source or appended to `.seen-assets` — even if nothing was claimable, so it stops re-flagging. Never silently leave a reviewed file unrecorded (it would nag every run) and never mark a file seen without actually reviewing it (that hides real material).
- **Stamp only what you reconciled.** If a source couldn't be fetched, report it and leave its baseline untouched (so it re-prompts next time) rather than stamping a stale state.
- **Scope:** touches only `resume/Resume-Facts.md`, the per-source baselines (`assets/.src-<name>.hash`), the seen-list (`assets/.seen-assets`), and `assets/sources.txt` (when declaring a new recurring source), plus refreshing local `gdoc` PDFs in place. It does not write `assets/.sources-status`, tune a resume, write a draft, or send anything.
