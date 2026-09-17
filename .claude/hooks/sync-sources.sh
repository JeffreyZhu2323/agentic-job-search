#!/usr/bin/env bash
# Source-freshness hook for ALL resume-fact ground-truth sources. Wired to BOTH
# UserPromptSubmit (catches the /tune-resume, /tune-resume-deep, /outreach slash
# commands -- they load the skill inline and never call the Skill tool) and
# PreToolUse/Skill (the programmatic skill-tool path). When Jeffrey runs
# tune-resume / tune-resume-deep / outreach, this does two
# things and flags what needs a Resume-Facts reconcile:
#   1. CHANGE detection: refresh each source in assets/sources.txt (Google Docs
#      -> exported PDF; GitHub repos -> claim-bearing tree hash) and flag which
#      changed since the last sync (hash vs stored baseline).
#   2. NOVELTY detection: flag any undeclared file that has appeared in assets/
#      (not a hidden state file, not sources.txt, not an already-declared source
#      localfile, not already seen) -- a new file probably carries new claimable
#      material worth reviewing.
# Cheap + free: download/hash/listing only, no model reasoning. The reconcile
# (read -> propose diff -> approve -> write) happens inside the skills, gated on
# the flag this writes. Never blocks the skill; fails open; distinguishes
# "nothing changed" from "couldn't check"; never clobbers a baseline on error.
#
# This hook is the ONLY writer of assets/.sources-status. sync-facts owns the
# per-source baselines (.src-<name>.hash) and the seen-list (.seen-assets), not
# this hook.
#
# Status file: zero or more typed lines, any combination of --
#   changed: <names>   a declared source's content moved
#   new: <paths>       an undeclared file appeared in assets/
#   error: <names>     a source couldn't be verified (offline/auth)
# or the single line `unchanged` when there is nothing to reconcile.

payload=$(cat)

# Only act when a job-search skill is invoked -- either via the Skill tool
# (PreToolUse payload: "skill":"...") or as a slash command typed by Jeffrey
# (UserPromptSubmit payload: "prompt":"/tune-resume..."). The slash-command path
# is the common one and does NOT call the Skill tool, so matching only the tool
# payload silently misses it. Anything else (incl. /sync-facts) is a no-op.
printf '%s' "$payload" \
  | grep -qE '"skill"[[:space:]]*:[[:space:]]*"(tune-resume|tune-resume-deep|outreach)"|"prompt"[[:space:]]*:[[:space:]]*"[[:space:]]*/(tune-resume-deep|tune-resume|outreach)' \
  || exit 0

# Resolve the project root robustly. This file lives at
# <root>/.claude/hooks/sync-sources.sh, so its own location pins the root
# without depending on CLAUDE_PROJECT_DIR being exported or the CWD being the
# project dir (either can be wrong depending on how the harness spawns the
# hook on Windows). Fall back to CLAUDE_PROJECT_DIR, then CWD, if self-location
# fails for any reason.
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
DIR="${SELF_DIR:-${CLAUDE_PROJECT_DIR:-.}}"
CONF="$DIR/assets/sources.txt"
STATUS="$DIR/assets/.sources-status"       # ephemeral: "unchanged" | "changed: <names>" | "error: <names>"
HELPER="$DIR/.claude/hooks/gh-claim-hash.sh"
[ -f "$CONF" ] || exit 0

trim() { printf '%s' "$1" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }

changed=""; errored=""; declared="|"   # declared holds |localfile|localfile| for the novelty scan
while IFS='|' read -r type name id localfile _ || [ -n "$type" ]; do
  type="$(trim "$type")"
  case "$type" in ''|\#*) continue ;; esac          # skip blank lines and comments
  name="$(trim "$name")"; id="$(trim "$id")"; localfile="$(trim "$localfile")"
  { [ -z "$name" ] || [ -z "$id" ]; } && continue
  [ -n "$localfile" ] && declared="$declared$localfile|"
  HASHFILE="$DIR/assets/.src-$name.hash"

  case "$type" in
    gdoc)
      pdf="$DIR/$localfile"; tmp="$pdf.tmp.$$"
      # Fetch to a temp file, then require HTTP success (-f), a non-empty body,
      # and a real PDF (%PDF magic) before atomically replacing the live file.
      # A private-doc redirect returns a 200 HTML login page that -f would not
      # catch, so the magic-byte check guards against clobbering the PDF with
      # non-PDF content and against a partial/interrupted download.
      if curl -sfL "https://docs.google.com/document/d/$id/export?format=pdf" -o "$tmp" \
         && [ -s "$tmp" ] && [ "$(head -c 4 "$tmp")" = "%PDF" ]; then
        mv -f "$tmp" "$pdf"
        # Hash the extracted TEXT, not the raw PDF bytes: Google Docs re-stamps
        # fresh metadata into the PDF container on every export, so sha256(raw
        # PDF) changes on every download even when the content is identical --
        # that would flag the source "changed" forever, no matter how often it
        # is synced. pdftotext output is stable across exports, so a text hash
        # is genuine content-based change detection (sync-facts stamps the
        # baseline the same way, so values match by construction). If pdftotext
        # is missing or yields nothing, treat it as "couldn't check" (errored)
        # rather than emitting a bogus hash that would falsely read unchanged.
        txt="$(pdftotext "$pdf" - 2>/dev/null)"
        if [ -n "$txt" ]; then
          new="$(printf '%s' "$txt" | sha256sum | cut -d' ' -f1)"
        else
          errored="${errored:+$errored, }$name"; continue
        fi
      else
        rm -f "$tmp"; errored="${errored:+$errored, }$name"; continue
      fi
      ;;
    github)
      new="$(bash "$HELPER" "$id")" || { errored="${errored:+$errored, }$name"; continue; }
      ;;
    *) continue ;;
  esac

  [ -z "$new" ] && { errored="${errored:+$errored, }$name"; continue; }
  old="$(cat "$HASHFILE" 2>/dev/null)"
  [ "$new" != "$old" ] && changed="${changed:+$changed, }$name"
done < "$CONF"

# Novelty scan: an undeclared, unseen file in assets/ is probably new claimable
# material. Exclude hidden state files (.src-*, .sources-status, .seen-assets),
# the sources.txt config, and files already declared as a source localfile
# (those are change-watched above). No baseline hash here -- just a seen-list
# that sync-facts appends to once it has reviewed a file.
SEEN="$DIR/assets/.seen-assets"
newfiles=""
for f in "$DIR"/assets/*; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  case "$base" in .*|sources.txt) continue ;; esac        # skip state files + config
  rel="assets/$base"
  case "$declared" in *"|$rel|"*) continue ;; esac         # skip declared source localfiles
  [ -f "$SEEN" ] && grep -qxF "$rel" "$SEEN" && continue    # skip already-seen
  newfiles="${newfiles:+$newfiles, }$rel"
done

# Compose the status: zero or more typed lines (changed / new / error), or the
# single line `unchanged`. changed+new+error can co-occur; a consumer reconciles
# on any changed: or new: line, warns on error:, skips on unchanged.
{
  [ -n "$changed" ]  && echo "changed: $changed"
  [ -n "$newfiles" ] && echo "new: $newfiles"
  [ -n "$errored" ]  && echo "error: could not check $errored"
  [ -z "$changed$newfiles$errored" ] && echo "unchanged"
} > "$STATUS"
exit 0
