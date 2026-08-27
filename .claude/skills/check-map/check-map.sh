#!/usr/bin/env bash
# check-map.sh — Layer-2 map-drift detector (Tier A: existence + broken paths).
# On-demand: run via the /check-map skill, or `bash .claude/skills/check-map/check-map.sh`.
# Warns only (never blocks the caller conceptually). Exit 0 = clean, 1 = drift found.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT"

CLAUDE_MD="CLAUDE.md"
drift=0

echo "== check-map: Tier-A drift scan against $CLAUDE_MD =="

# 1. Skill -> map: every skill dir must be referenced by its path in CLAUDE.md.
for d in .claude/skills/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  if ! grep -q "\.claude/skills/$name/" "$CLAUDE_MD"; then
    echo "  ! skill '$name' exists but is not on the map (add it to CLAUDE.md)"
    drift=1
  fi
done

# 2. Map -> skill: every skill path named in CLAUDE.md must exist on disk.
while read -r p; do
  [ -z "$p" ] && continue
  if [ ! -d "$p" ]; then
    echo "  ! CLAUDE.md references a missing skill dir '$p'"
    drift=1
  fi
done < <(grep -oE '\.claude/skills/[a-z0-9-]+/' "$CLAUDE_MD" | sort -u)

# 3. Broken structural paths (curated allow-list; update if the structure changes).
structural_paths=(
  "Recruiting-Strategy-2027.md"
  "data/" "data/SCHEMA.md" "data/applications.csv" "data/contacts.csv" "data/outreach.csv"
  "resume/" "resume/Resume-Facts.md" "resume/resume-ai.tex" "resume/resume-mlds.tex"
  "companies/" "assets/" "archive/"
)
for p in "${structural_paths[@]}"; do
  if [ ! -e "$p" ]; then
    echo "  ! CLAUDE.md structural path '$p' is missing on disk"
    drift=1
  fi
done

# 4. Description drift (soft staleness signal): a skill's frontmatter
#    `description:` is its contract summary and the source of its CLAUDE.md map
#    line. If it changed since the map was last confirmed in sync, the map entry
#    may be stale -> hand to /sync-docs. A body-only edit does NOT flip this
#    (matches "map the contract, not the implementation"). Baselines under
#    .claude/.docmap/ are written by /sync-docs, never here.
DOCMAP=".claude/.docmap"
for d in .claude/skills/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  [ -f "$d/SKILL.md" ] || continue
  if ! cur="$(bash .claude/skills/check-map/map-hash.sh "$name" 2>/dev/null)"; then
    echo "  ~ skill '$name': SKILL.md has no readable description - map entry unverifiable (fix frontmatter, then /sync-docs)"
    drift=1; continue
  fi
  old="$(cat "$DOCMAP/$name.hash" 2>/dev/null)"
  if [ -z "$old" ]; then
    echo "  ~ skill '$name': no doc-sync baseline yet - map entry unverified (run /sync-docs)"
    drift=1
  elif [ "$cur" != "$old" ]; then
    echo "  ~ skill '$name': description changed since last doc-sync - map entry may be stale (run /sync-docs)"
    drift=1
  fi
done

if [ "$drift" -eq 0 ]; then
  echo "  OK map in sync - no Tier-A drift"
fi
exit "$drift"
