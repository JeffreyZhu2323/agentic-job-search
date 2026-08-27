---
name: sync-docs
description: Reconcile CLAUDE.md's Canonical-files map with the skills as they actually are. When a skill's contract has drifted from its map entry (or a skill is new or removed), propose a map-line update and write only what Jeffrey approves, then re-baseline so /check-map stops flagging it. The Layer-3 human-gated reconcile that /check-map hands off to; run it after changing a skill's contract or whenever /check-map reports soft drift.
---

# Sync CLAUDE.md map from the skills

Reconcile the CLAUDE.md "Canonical files" map against the skills as they actually exist. This is the human-approved update of the map's *semantic accuracy* — the counterpart to `check-map`, which only detects that something may have drifted. **check-map is the cheap mechanical tripwire; sync-docs does the judgment and the writing.** (Same shape as `sync-sources` -> `sync-facts`: a deterministic detector feeds a human-gated reconcile.)

Map wording is a judgment call — propose, never auto-rewrite.

## Scope
- Reconciles the **skill entries** in CLAUDE.md's Canonical-files map: role, when to use it, and what it touches (outputs, side effects, cross-skill handoffs) — **the contract, not the implementation**.
- Follows the CLAUDE.md Upkeep rules: map the contract not the implementation; don't document data/history/transient state; keep entries tight.
- Writes only `CLAUDE.md` and the per-skill map baselines (`.claude/.docmap/<name>.hash`). Does not touch skill behavior, data, or resumes.
- Out of scope for now: `SCHEMA.md` and non-skill prose in CLAUDE.md (candidate snapshot, goals, dials). Extend later if those start drifting.

## Procedure
1. **Find what to reconcile.** Run the detector:
   ```
   bash .claude/skills/check-map/check-map.sh
   ```
   Reconcile the skills it flags:
   - `~` soft — a skill's `description` changed since last doc-sync, or has no baseline yet (map entry unverified).
   - `!` hard — a skill on disk with no map entry (needs a new entry), or a map entry whose dir is gone (needs removal).
   If invoked from another skill for specific skills, reconcile just those.
2. **For each skill to reconcile**, read its `SKILL.md` (frontmatter `description` + enough of the body to know its real contract) and its current CLAUDE.md map line. Decide whether the map line still accurately states the skill's **role, when to use it, and what it touches**.
3. **Propose a diff — suggestions only.** Per skill, present:
   - **Update** — the current map line vs a proposed rewrite, when the contract drifted (changed side effect, handoff, output, trigger).
   - **Add** — a proposed new entry for a skill that has none.
   - **Remove** — a map entry whose skill dir is gone.
   - **No change** — say so explicitly when the line is still accurate (it still gets re-baselined in step 5).
   Keep proposals tight and in the map's existing style. What the entry says is Jeffrey's call.
4. **Write on approval.** Apply only the map-line changes Jeffrey approves to `CLAUDE.md`. Nothing unapproved goes in.
5. **Re-baseline each reconciled skill** so check-map stops flagging it, using the shared hasher so the value matches check-map's by construction:
   ```
   mkdir -p .claude/.docmap
   bash .claude/skills/check-map/map-hash.sh <name> > .claude/.docmap/<name>.hash
   ```
   Baseline a skill only once its map line is confirmed accurate (edited-and-approved, or approved as-is). Do **not** baseline a skill whose drift Jeffrey deferred — leave it flagged.
6. **Confirm** to Jeffrey exactly which map entries changed and which were re-baselined (and anything left for later).

## Guardrails
- **Judgment gate — nothing enters CLAUDE.md without Jeffrey's approval.** Propose; never auto-rewrite the map.
- **Contract, not implementation.** A body-only SKILL.md edit that doesn't change the contract needs no map change — confirm "no change" and re-baseline. Rewrite the line only when role / when-to-use / what-it-touches actually moved.
- **Baseline only what's accurate.** Re-baselining tells check-map "the map matches this skill's current contract." Never stamp a skill whose map line is still wrong or was deferred.
- **Detection stays in check-map.** This skill does not re-implement existence/path checks; it consumes check-map's output and does the semantic reconcile.
