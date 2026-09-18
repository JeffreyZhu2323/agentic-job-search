---
name: inbox
description: Read new messages in Jeffrey's "Recruiting" Gmail label (via the read-only gmail-recruiting MCP server) and take whatever recruiting actions they warrant — not just status changes. Use when Jeffrey runs /inbox to process his recruiting email. Classifies each new message, then proposes a consolidated plan across the whole tracker (applications.csv status moves, contacts.csv adds/edits, outreach.csv + verbatim thread logs for anything inbound, next-action/deadline flags, and handoffs like a resume tune or an /outreach reply), writes only what Jeffrey approves in one gate, and advances a processed-message watermark so re-runs never double-count. MANUAL ONLY (never auto-triggered) and READ-ONLY on email (never sends, labels, or deletes).
---

# Inbox — process recruiting email into the tracker

Manual, on-demand triage of Jeffrey's recruiting inbox. Read the new
`Recruiting`-labeled messages, understand each one, and do the useful recruiting
thing with it. You are **not** limited to flipping `applications.csv` status —
you have latitude to update any of the tracker files, draft a reply for the
`/outreach` skill to log, flag a deadline, or surface a decision. The one
invariant is this repo's standing rule: **propose, then write only what Jeffrey
approves.** Broad action space, single human gate.

## Before anything: prerequisites
- The `gmail-recruiting` MCP server must be connected (see `tools/gmail-mcp/README.md`).
  If its tools aren't available or it errors "Not authenticated," stop and tell
  Jeffrey to complete the one-time OAuth setup / restart Claude Code — don't guess
  at inbox contents.
- **Email access is read-only.** You can only `list_recruiting`, `read_message`,
  and `search`. You cannot send, reply, label, archive, or delete. Any "reply"
  you produce is a *draft* handed to `/outreach`; Jeffrey sends it himself.

## Read first (ground truth)
1. `data/SCHEMA.md` — the controlled columns and enum values for all three CSVs.
   **Every write below must use only its allowed values.** Read it before writing.
2. `data/applications.csv`, `data/contacts.csv`, `data/outreach.csv` — current
   state, so you match against existing rows instead of duplicating them.
3. `data/.inbox-state` (JSON: `{"last_run": "...", "processed_ids": [...]}`) — the
   watermark of message IDs already handled. Create it (empty `processed_ids`) if
   missing. If a message body you'll draft from is candidate-facing prose, also
   read `resume/voice.md` and apply `CLAUDE.md` / `STRATEGY.md` phrasing + grad-school
   policy (same as `/outreach`).

## Procedure
1. **Fetch new mail.** Call `list_recruiting` (default `query: "newer_than:30d"`,
   raise if Jeffrey asks for more history). Drop any message whose `id` is already
   in `processed_ids` — those are done. For each remaining message, call
   `read_message(id)` to get the full body. If there's nothing new, say so and stop.
2. **Classify each message** into what it actually is, e.g.:
   - application status signal — `oa` / assessment invite, `phone_screen` /
     `recruiter_screen` scheduling, `onsite`, `offer`, `rejected`, request for info;
   - inbound recruiter contact (cold or continuing a thread);
   - a reply on an existing outreach thread (referral, scheduling, thank-you);
   - logistics/info (event, portal confirmation) with no state change;
   - noise (job-board digests, newsletters, "your application was viewed") — ignore,
     but still mark processed so they don't resurface.
   For each real signal, quote the **specific sentence** that justifies it, so
   Jeffrey can sanity-check your read at a glance.
3. **Match to the tracker.** Tie each message to an existing row by company + role
   (use `req_url` / sender domain / thread when they help), and to a `contact_id`
   by name or email.
   - **One confident match** → propose the update in place.
   - **Zero or multiple matches** → do **not** guess. Surface it as a question in
     the plan (which row, or new row?).
4. **Decide the actions** (your latitude — pick what fits, combine freely):
   - `applications.csv`: move `status` forward in place; set `next_action` /
     `next_action_date` (e.g. "complete OA" with its due date, "reply to schedule",
     "respond to offer"); add a dated `notes` breadcrumb; create a new row for a
     genuinely new opportunity (`source = recruiter_inbound` for cold recruiter mail).
   - `contacts.csv`: add a recruiter/referrer not yet on file, or fill a missing
     email/title on an existing one.
   - `outreach.csv` + `data/threads/<CON-id>.md`: log any **inbound** message as an
     `inbound` touch (append the message **verbatim** to the thread in the same
     step — the standing SCHEMA rule), set `status` to whose court the ball is in.
     A cold recruiter reaching out is the `/outreach` recruiter-inbound intake case —
     follow that skill's intake shape (contact + inbound row + any named role) rather
     than reinventing it.
   - **Handoffs** (propose, don't silently run): if a recruiter wants a resume,
     recommend `/tune-resume` or `/tune-resume-deep`; if a reply is needed, offer to
     draft it via `/outreach`; if an interview is set, note prep and (for dream/high
     targets) the `companies/<company>/<role>/` workspace.
   - **Deadlines**: pull any date (OA window, interview time, offer deadline) into a
     `next_action_date` so it shows up in "what's due."
5. **Present one consolidated plan and wait.** List it per message: sender +
   subject + date, your one-line classification with the quoted evidence, and the
   exact proposed writes (which file, which row/`app_id`, before → after). Group the
   open questions (unmatched rows, new-vs-existing, honesty calls) as a single
   numbered list so Jeffrey can answer inline. **Do not write yet.** A question in
   his reply is not a decision (same rule as the tune skills): answer it and keep
   that item open until he actually decides.
6. **On his approval — apply, in one pass.** Write only the approved actions, using
   only `SCHEMA.md` enum values; quote any CSV field containing a comma; keep
   `outreach.csv` append-only with its matching verbatim thread append; update
   existing `applications.csv` rows in place (don't duplicate). Then **advance the
   watermark**: add every message `id` you processed this run (including ignored
   noise) to `processed_ids`, set `last_run` to today, and write `data/.inbox-state`
   (keep the most recent ~1000 ids; drop older). Run any handoff skills only if
   Jeffrey approved them.
7. **Report** what changed: rows touched (with `app_id`s), contacts/outreach added,
   threads appended, deadlines now due, and any handoff you recommend as the next step.

## Guardrails
- **Manual only.** This skill runs when Jeffrey invokes `/inbox`. Never wire it to a
  hook or schedule without his explicit say-so.
- **Read-only on email; write-only-what's-approved on the tracker.** No sends, no
  label/delete. No CSV/thread write without Jeffrey's OK in step 5.
- **Enums are law.** Only `data/SCHEMA.md` values. IDs are permanent — new rows take
  the next free number; never renumber.
- **Idempotent.** The watermark is what prevents double-logging; always update it on
  a successful run, and never re-process an id already in `processed_ids`.
- **Voice.** Any candidate-facing text you draft goes through `resume/voice.md` and
  the phrasing dials, then to `/outreach` to actually log/send — this skill doesn't
  send.
