# Recruiting data schema (single source of truth)

Three CSVs, three grains. Join on the ID columns. Any agent (or you) reading/writing
these files MUST use the controlled values below — consistent enums are what make the
data queryable and automatable. Dates are ISO `YYYY-MM-DD`. Quote any field containing a comma.

---

## `applications.csv` — one row per role (a state machine; status changes in place)

| column | meaning | allowed / format |
|---|---|---|
| `app_id` | stable key | `APP-001`, `APP-002`, … |
| `company` | employer | free text |
| `role_title` | role as posted | free text |
| `team` | org/team if known | free text (blank ok) |
| `location` | primary location | free text |
| `req_url` | job posting link | URL (blank ok) |
| `source` | how it entered your pipeline | `cold` \| `referral` \| `recruiter_inbound` \| `career_fair` \| `warm_intro` |
| `resume_variant` | which resume you sent | `ai` \| `mlds` \| `custom` (blank if not yet sent) |
| `date_applied` | date submitted | `YYYY-MM-DD` (blank until applied) |
| `status` | current pipeline stage | `to_apply` \| `applied` \| `recruiter_screen` \| `oa` \| `phone_screen` \| `onsite` \| `offer` \| `rejected` \| `withdrawn` \| `no_response` |
| `priority` | how much it matters | `dream` \| `high` \| `mid` \| `insurance` |
| `contact_id` | linked person (referrer/recruiter) | `CON-xxx` (blank ok) |
| `next_action` | the very next thing YOU do | free text |
| `next_action_date` | when it's due | `YYYY-MM-DD` (blank if none) |
| `notes` | anything else | free text |

## `contacts.csv` — one row per person (a dimension; durable facts)

| column | meaning | allowed / format |
|---|---|---|
| `contact_id` | stable key | `CON-001`, … |
| `name` | full name | free text |
| `company` | where they work | free text |
| `title` | their role | free text |
| `relationship` | who they are to you | `recruiter` \| `alum` \| `friend` \| `hiring_manager` \| `referrer` \| `professor` \| `other` |
| `linkedin` | profile URL | URL (blank ok) |
| `email` | email | (blank ok) |
| `phone` | phone | (blank ok) |
| `other_handle` | WeChat/WhatsApp/etc. | free text (blank ok) |
| `source` | how you know / got connected | free text |
| `notes` | anything else | free text |

## `outreach.csv` — one row per touch (an append-only event log; never edit past rows except `status`)

| column | meaning | allowed / format |
|---|---|---|
| `outreach_id` | stable key | `OUT-001`, … |
| `date` | date of the touch | `YYYY-MM-DD` |
| `contact_id` | who | `CON-xxx` |
| `company` | denormalized for quick filtering | free text |
| `channel` | medium | `linkedin` \| `email` \| `wechat` \| `whatsapp` \| `phone` \| `in_person` |
| `direction` | who initiated this message | `inbound` (they → you) \| `outbound` (you → them) |
| `type` | purpose | `cold_outreach` \| `referral_ask` \| `recruiter_inbound` \| `follow_up` \| `thank_you` \| `scheduling` \| `other` |
| `app_id` | related application | `APP-xxx` (blank ok) |
| `status` | whose court the ball is in | `awaiting_me` \| `awaiting_them` \| `closed` |
| `next_action` | next thing YOU do (if any) | free text (blank ok) |
| `next_action_date` | when | `YYYY-MM-DD` (blank ok) |
| `summary` | what happened | free text |

## `threads/` — verbatim message history (one Markdown file per contact)

`data/threads/<CON-id>.md` holds the **full verbatim** back-and-forth with a contact (both
directions), dated, append-only, newest at bottom. The `outreach.csv` `summary` field is a
condensed index of each touch; the thread file is the exact wording.

**Standing rule: every `outreach.csv` write has a matching thread append.** Whenever a row is
added to `outreach.csv` — outbound or inbound, drafted via `/outreach` or logged by hand —
append that message **verbatim** to `data/threads/<CON-id>.md` in the same step. The CSV row
is the summary/index; the thread entry is the exact text; they are written together so the
verbatim history never desyncs. (The `/outreach` skill also reads the thread file before drafting.)

Not every contact needs one; it's created on the first logged touch. Cross-reference each
entry with its `outreach_id`. Held (not-yet-sent) drafts go under a clearly-labeled
"pending (not sent)" note and are promoted into the thread once actually sent.

---

### Conventions
- **IDs are permanent.** Never renumber. New rows take the next free number.
- **`applications.status` moves forward in place**; you overwrite the cell as the stage changes.
- **`outreach` is append-only** — each message is a new row; don't rewrite the past, only flip a row's `status` to `closed` when the thread ends.
- **"What's due" = ** any `applications` or `outreach` row whose `next_action_date` ≤ today, plus any `outreach` with `status = awaiting_me`.
- **Staleness rule of thumb:** `applied` with no response after ~10 days → consider a `follow_up`; a `referral_ask` `awaiting_them` after ~5 days → gentle nudge.
