---
name: outreach
description: Draft a recruiting message (recruiter cold outreach, referral ask to an alum/contact, reply to an inbound recruiter, or a follow-up) tuned to the person and the phrasing dials, then log it to the tracker on approval. Use when Jeffrey wants to write or reply to someone in his job search. DRAFT ONLY — never sends; Jeffrey sends it himself.
---

# Draft a Recruiting Message

Act as a tech-recruiting expert helping Jeffrey write a message to a real person in his job search. The message must read as **genuinely human and specific to the recipient** — never templated, generic, or "produced." This is the most personal channel, so warmth and specificity matter more than anywhere else.

**Draft only. Never send.** Jeffrey sends it himself; this skill produces the text and logs the touch.

**Scope.** *Drafting* is outbound only — this skill drafts messages Jeffrey sends, never inbound. *Logging* depends on type: a **`recruiter_inbound` run owns full intake** and persists the contact, the inbound message (row + thread), and the application **immediately at step 3** — invoking `/outreach` on an inbound is itself the signal that these matter, so they aren't gated on the reply. Other types log only the outbound message, on approval. A standalone inbound Jeffrey isn't replying to is logged outside this skill, but by the same standing rule (`SCHEMA.md` `threads/`): an `outreach.csv` row **plus a verbatim append to `data/threads/<CON-id>.md`**.

## Inputs (ask for whatever isn't given)
- **Who** — the recipient. Either an existing `contacts.csv` row (`CON-xxx`) or a new person (name, company, title, how Jeffrey knows them / how they connected).
- **Type** — `cold_outreach` | `referral_ask` | `recruiter_inbound` (a reply) | `follow_up`.
- **Context / goal** — what Jeffrey wants from this message, plus any thread history (paste of their message, prior touches).
- **Channel** — `linkedin` | `email` | `wechat` | `whatsapp` | `phone` | `in_person`.
- **Related application** — `APP-xxx` if this ties to a specific role (optional).

## Reads (just-in-time — pull each only when its trigger fires; do NOT read them all upfront)
Eager upfront reads waste tokens: a new-stranger cold outreach needs almost none of these. Read each at the step noted.

| File | When to read | Notes |
|---|---|---|
| `CLAUDE.md` (dials, positioning) | **never re-read** | auto-loaded into context at session start; already available |
| recipient's row in `data/contacts.csv` | step 1, always | targeted lookup (grep by name / `CON-id`), not the whole file |
| `data/threads/<CON-id>.md` (verbatim history) | step 1, **only if the contact exists** | the durable full history; a new stranger has none. Chat sessions don't persist, so this file, not this conversation, is the record |
| recipient's rows in `data/outreach.csv` | step 1, **only if existing contact with prior touches** | pull the state (status / next_action); the thread file already carries the content |
| `data/applications.csv` | step 2 read if tied to an existing `APP-xxx`; **written at step 3** on a recruiter_inbound that names a role | the linked role's details/status |
| `resume/Resume-Facts.md` | step 4, **only if the draft cites Jeffrey's background** | truthful-claim boundary |
| `data/SCHEMA.md` | **steps 3 and 6, before writing any rows** (intake writes; reply log) | controlled enum values |

## Procedure
0. **Sync resume-fact sources first (auto-gated, cheap).** A hook has already refreshed all configured ground-truth sources (`assets/sources.txt` — UCSF research notes + watched GitHub project repos) and written a change flag. Read `assets/.sources-status`:
   - `unchanged` or missing -> skip this step, go to 1. (Common case: no cost, no prompt.)
   - `changed: <sources>` -> those sources have new material since `Resume-Facts.md` was last synced. Since outreach only touches `Resume-Facts.md` when the message references Jeffrey's background, this is optional here: mention which changed and ask whether to reconcile now or skip. If yes: run the `sync-facts` procedure for the named sources — refresh + read each (a `gdoc` from its local PDF; a `github` repo from its committed README/results at HEAD), propose a tight diff of new/changed **claimable** facts as suggestions only (Jeffrey decides — honesty boundary); write only approved lines into `resume/Resume-Facts.md` (CAN CLAIM); then stamp each reconciled source (`sha256sum "<local-pdf>" | cut -d' ' -f1 > assets/.src-<name>.hash` for a gdoc, `bash .claude/hooks/gh-claim-hash.sh <owner/repo> > assets/.src-<name>.hash` for a github repo). Do not write `assets/.sources-status` (the hook owns it). Then continue.
   - `new: <files>` -> undeclared files have appeared in `assets/`. As with changed sources this is optional here (only matters if the message cites Jeffrey's background): mention them and offer to review via the `sync-facts` procedure — read each, propose claimable-fact suggestions (Jeffrey's call), write approved lines into `resume/Resume-Facts.md`, mark it seen (`assets/.seen-assets`), and declare a recurring source in `assets/sources.txt`. Do not write `assets/.sources-status`. (`changed:` and `new:` can co-occur.)
   - `error: <sources>` -> the hook couldn't verify those sources (network/auth). Mention their facts may be stale, but do NOT block — continue.
1. **Identify the recipient** with a targeted lookup in `contacts.csv` (by name / `CON-id`), not a full-file read. **If new:** note the details to add on approval and skip the next two reads (no history exists yet). **If existing:** read the contact's verbatim thread at `data/threads/<CON-id>.md` so the message fits what was actually said, and pull their `outreach.csv` state (status / next_action) only if there are prior touches. If Jeffrey pastes new inbound/prior messages this run that aren't in the file yet, treat those as source of truth and capture them into the thread (immediately at step 3 for a recruiter_inbound; otherwise at logging, step 6).
2. **Gather context** — the goal, the role (if any; read the linked `APP-xxx` row from `data/applications.csv` only if the message ties to a specific role), and what's genuinely specific about this person/company (their team, something they said, a real connection). Specificity is what keeps it from reading generic; if there's nothing specific, ask Jeffrey for a detail rather than padding with filler.
   - **First contact with a stranger (on-demand, before drafting):** if the recipient is someone Jeffrey has no relationship with and no local context on, offer to research them first — spawn one context-gathering subagent, then draft from what it returns. Key this off *stranger-ness, not message type*: it applies to `cold_outreach` **and to a cold `referral_ask`** — a referral ask to someone he's never met (an alum, a target-company employee). Jeffrey's referral asks are typically cold, so this is the common case, not the exception. **Skip it** for inbound replies, follow-ups, and referral asks to people he genuinely already knows (context is already local). **Guardrails on the result:** use only professional-public facts (their team, role, public work, a real shared thread); treat every researched fact as *uncertain* — reference it lightly, never assert a shaky detail; **never parrot personal details**, which reads as creepy and sinks the message.
3. **Commit intake immediately (recruiter_inbound only) — do NOT wait for the reply.** Invoking `/outreach` on an inbound *is* the signal that this contact, message, and role matter, so persist them now (read `data/SCHEMA.md` for enums first, then write in order):
   - **Contact** — if the recruiter is new, append a `contacts.csv` row (`CON-xxx`); otherwise confirm the existing one.
   - **Inbound message** — append an `outreach.csv` row (`direction=inbound`, `type=recruiter_inbound`, today's `date`, `status=awaiting_me` since a reply is owed) **and** append the pasted message verbatim to `data/threads/<CON-id>.md` (the standing CSV+thread pairing).
   - **Application** — if the recruiter names a concrete role: create/update an `applications.csv` row (`source=recruiter_inbound`, link `contact_id`, `status=to_apply` or `recruiter_screen`), confirming company/role/priority with Jeffrey. If a resume is going out for it now, hand to `/tune-resume` or `/tune-resume-deep` (they own the app row + resume). If no concrete role is named yet, skip the app row.
   Confirm the written rows back to Jeffrey, then continue. For any non-`recruiter_inbound` type, **skip this step** (their logging happens on approval, step 6).
4. **Draft the message** (if it cites Jeffrey's background, first read `resume/Resume-Facts.md` for the truthful-claim boundary), tuned to:
   - **Audience + channel** — re-tune warmth to the person. A LinkedIn DM to a recruiter is warmer and looser than a formal email; a referral ask to an alum is personal and low-pressure. Match how a sharp, friendly human actually writes, not a form letter.
   - **Subject line (when the channel has one)** — for `email` and LinkedIn InMail, include a short, specific, low-key subject line above the message (a plain reason-for-writing, never clickbait). Skip it for plain LinkedIn DMs / connection notes, WeChat, WhatsApp, phone, and in-person, where the first line is the opener. When the send path is unclear, offer one anyway and note it's optional.
   - **The dials** (from `CLAUDE.md`) — human (no buzzword tells, no formulaic parallelism, no dash-as-connector), specific, tight. Lead with why *them* / why *now*, make the ask clear and easy to say yes to, keep it short.
   - **Type-specific shape:**
     - `cold_outreach` — a real reason you're reaching out to *them*, a crisp line on fit, a low-friction ask.
     - `referral_ask` — Jeffrey is asking a stranger to put *their name* on him, so lead warm and human, keep it light, and be genuinely grateful without groveling. **Human-first, substance relocated:** open on the real connection (shared school/team/background, their public work), then carry *one* concrete, plain-English reason he fits — not a stack of tools, metrics, or jargon. Push the full factual load to the resume + short blurb he offers to send; the message is the invitation, the resume is the evidence. Keep tool names only when the recipient clearly speaks that language, and even then hold it to one line. **Default to cold** (Jeffrey's usual case: an alum or target-company employee he's never met): open like a cold message — a genuine reason he's contacting *them* — then the ask; don't fake a "reconnect" with someone he doesn't know. Only if there's a real prior relationship, warm-reconnect first. Make the ask clear and low-friction (specific role, offer to send resume + blurb), give an easy out ("no worries if not"), and close with sincere thanks for even considering it.
     - `recruiter_inbound` reply — answer their questions, steer toward the roles/location that fit, keep momentum. **Resume handoff:** if the reply sends a resume for a concrete role, verify a current tuned resume actually fits it; if not, offer to tune before finalizing, and let Jeffrey pick `/tune-resume` (normal target) or `/tune-resume-deep` (dream / high-value target). Skip this when the role isn't pinned down yet — reply to clarify first, tune later.
     - `follow_up` — brief, non-pushy, add a reason to re-engage (new info, genuine interest), never guilt.
5. **Interactive review** — show the draft and **wait**. Offer 1-2 alternates only if a real fork exists (e.g. warmer vs. more direct). Iterate on Jeffrey's edits until he says it's good.
   - **Advise when to send (once the wording is settled).** Recruiters and busy contacts respond best to messages that land at the top of a working-hours inbox, so give Jeffrey a concrete send window, not just the text. Default heuristic: **Tuesday–Thursday, mid-morning recipient-local (~8–11am); avoid weekends, Friday afternoons, and Monday before ~9am** (inbox pileup). Then adjust for:
     - **Recipient timezone** — infer it from the contact's data (phone country code, `location`, company HQ) and convert the target window to *Jeffrey's* local time so the advice is actionable (e.g. a `+86` recruiter's Tue 9am is Jeffrey's Mon evening). If the timezone is genuinely unclear, say so and give the recipient-local window.
     - **Type / urgency** — for `follow_up` and `cold_outreach` (including cold `referral_ask`), it's worth holding a day or two to hit the good window. For a `recruiter_inbound` reply or `scheduling` where momentum matters, **send promptly beats perfectly-timed** — don't tell Jeffrey to sit on a hot reply for two days to catch a Tuesday.
     - **Channel** — email and LinkedIn DMs sit in an inbox, so timing is a soft optimization, not a hard gate; phone/in-person are genuinely time-bound. Don't over-engineer an async channel.
   - Keep it to a line or two, and if the current moment already falls in a good window, just say "fine to send now."
6. **Log the outbound message on approval** — after Jeffrey approves the wording, read `data/SCHEMA.md` for controlled values (if not already read at step 3), then:
   - If the recipient is new **and wasn't already added at step 3**, append a `contacts.csv` row (next `CON-xxx`, per SCHEMA).
   - **Confirm he's actually sending it** (approval of the wording is the default "sent" convention, but check). If sent: `status` = `awaiting_them`. If he's holding it: keep a `next_action` to send it, and set `status` accordingly.
   - Append an `outreach.csv` row: next `outreach_id`; today's `date`; `contact_id`; `company`; `channel`; `direction` = `outbound`; `type`; `app_id` if linked; `status` per above; `next_action` / `next_action_date` if a follow-up is expected; `summary` of the message. Quote fields containing commas.
   - **Update the verbatim thread.** Append the approved message (verbatim, dated, with direction and its `OUT-id`) to `data/threads/<CON-id>.md`, creating the file if it's the first touch. If Jeffrey pasted any prior/inbound messages this run that aren't in the file yet, append those verbatim too so the thread stays complete. This file is the durable full history; the `outreach.csv` summary is just the index. If the message is **held** (not yet sent), record it under a clearly-labeled "pending (not sent)" note and promote it into the thread once actually sent.
   - **On a recruiter_inbound reply:** if the reply was actually sent, flip the step-3 inbound row's `status` to `closed` (now answered); if held, leave it `awaiting_me`.
   - Confirm the appended row(s) back to Jeffrey.

## Guardrails
- **Draft only — never send.**
- **Never templated.** If the draft could be sent to anyone, it's wrong — make it specific to this person or ask Jeffrey for the detail that makes it specific.
- **Log only after approval**, using `SCHEMA.md`'s controlled values.
- **Truthful** — any claim about Jeffrey's background comes from `Resume-Facts.md`.
- Re-tune warmth to the channel: the more personal it is, the less "produced" it should sound.
