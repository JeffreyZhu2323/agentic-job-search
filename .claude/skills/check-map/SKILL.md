---
name: check-map
description: On-demand check that CLAUDE.md's map is in sync with reality (the Layer-2 mechanical detector, Tier A, run by hand rather than via a hook). Flags skills on disk that aren't on the map, map entries pointing at missing skills, and broken structural paths. Run it anytime, and during the periodic map review. Warns only; fixes stay in-band.
---

# Check Map Drift

Run the Tier-A drift detector against `CLAUDE.md` and report the result. This is Layer 2 (mechanical detection) invoked manually; it does not auto-fix.

## Procedure
1. Run: `bash .claude/skills/check-map/check-map.sh`
2. Relay its output.
3. If it reports drift, act by marker type:
   - **`!` hard drift** (skill dir with no map entry; map path with no dir; broken structural path): offer to fix each **in-band** — add the missing entry or correct the stale path. Confirm the wording with Jeffrey first; *detection* is mechanical, *what the entry says* is judgment.
   - **`~` soft drift** (a skill's `description` changed since last doc-sync, or has no baseline yet): the map entry may be stale. Offer to run **`/sync-docs`**, which reads the skill, proposes a corrected map line, writes on approval, and re-baselines. check-map only flags the possibility; sync-docs makes the semantic call.

## Scope (Tier A only)
- **Detects (hard, `!`):** a skill dir with no `CLAUDE.md` entry; a `CLAUDE.md` skill path with no dir; a missing structural path from the curated allow-list in the script.
- **Detects (soft, `~`):** a skill whose `SKILL.md` frontmatter `description` (its contract summary, the source of its map line) changed since the map was last confirmed in sync, or that has no baseline yet — a signal the map entry may be stale. Handed to `/sync-docs`. Baselines live under `.claude/.docmap/` and are written by `/sync-docs`, never here.
- **Does NOT detect:** whether a flagged description is *actually* wrong (that judgment is `/sync-docs`'s); internal skill behavior below the contract (a body-only edit doesn't flip the soft signal); or judgment-content staleness like settled decisions and phrasing dials (Layer-3 human review).
- If the directory structure changes, update the `structural_paths` allow-list in `check-map.sh`.
