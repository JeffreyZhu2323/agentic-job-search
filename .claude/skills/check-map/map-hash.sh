#!/usr/bin/env bash
# Print the "contract hash" of a skill: a hash of its SKILL.md frontmatter
# `description:` line -- the skill's contract summary and the source of its
# CLAUDE.md map entry. Shared by check-map.sh (drift detection) and the
# sync-docs skill (baseline stamping) so the compared value and the stored
# baseline are computed identically (no drift). A body-only edit to the SKILL.md
# does not change this, matching "map the contract, not the implementation".
name="$1"
[ -n "$name" ] || { echo "usage: map-hash.sh <skill-name>" >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
md="$ROOT/.claude/skills/$name/SKILL.md"
[ -f "$md" ] || { echo "no SKILL.md for '$name'" >&2; exit 1; }

# Strip the leading `description:` prefix and any trailing CR so the hash is
# line-ending-independent (this repo's SKILL.md files are CRLF; other tools write
# LF -- without this, a pure EOL normalization would look like a contract change).
desc="$(sed -n 's/^description:[[:space:]]*//p' "$md" | head -1 | tr -d '\r')"
[ -n "$desc" ] || { echo "no description in '$name' SKILL.md" >&2; exit 3; }
printf '%s' "$desc" | sha256sum | cut -d' ' -f1
