#!/usr/bin/env bash
# Print a hash of a GitHub repo's claim-bearing content (README, notebooks,
# results files) at default-branch HEAD. Used by BOTH the sync-sources detector
# hook and the sync-facts stamp step, so the compared value and the stored
# baseline are computed identically (no drift). Exits nonzero with no output on
# any gh failure (offline / auth / missing scope), so callers can leave baseline
# state untouched rather than corrupt it.
repo="$1"
[ -n "$repo" ] || { echo "usage: gh-claim-hash.sh owner/repo" >&2; exit 2; }

raw="$(gh api "repos/$repo/git/trees/HEAD?recursive=1" \
        --jq '[.tree[]
               | select((.path|ascii_downcase) as $p
                        | ($p|contains("readme")) or ($p|contains("result")) or ($p|endswith(".ipynb")))
               | .sha] | join(",")')" || exit 1

printf '%s' "$raw" | sha256sum | cut -d' ' -f1
