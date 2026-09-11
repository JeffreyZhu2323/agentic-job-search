#!/usr/bin/env python3
"""voice-lint.py -- PreToolUse gate that blocks a resume write when the changed
text carries AI-writing tells (buzzword stacking, cliches, the "not just X but Y"
construction, em/en dashes). Deterministic and near-free: pure regex, no API call,
no model reasoning. It is the mechanical floor under the soft, in-loop voice pass
the tune-resume skills already do -- catches the high-precision tells so a bad
line never reaches resume.pdf, and leaves the fuzzy "does it sound like Jeffrey"
judgment to the LLM voice judge in eval/.

Wired to PreToolUse on Write|Edit|MultiEdit. Fails OPEN: any parse/logic error
exits 0 (allow) so the linter can never wedge a legitimate write.

SCOPE: resume .tex files only (all Jeffrey's prose, no third-party text). Thread
files are deliberately excluded -- they log recruiters' verbatim messages next to
his drafts, and rewriting someone else's words would be wrong.

Block behavior: exit code 2 with the findings on stderr, which Claude Code feeds
back to the model so it rewrites and re-issues the write.

Tuning: edit BLOCK below. Each entry is (regex, label); matching is
case-insensitive and word-bounded. Move a term out to soften it; the list is
curated for precision (few false positives on ML/stats resume prose), so terms
with legitimate technical uses (orchestrate, harness, architect, dynamic,
proficient, streamline, state-of-the-art, vital) are intentionally NOT here.
"""
import sys, os, re, json

# High-precision AI-writing tells. (pattern, human label). Case-insensitive.
_PATTERNS = [
    (r"\bleverag(?:e|ed|es|ing)\b",              'buzzword "leverage" (use "use"/"used")'),
    (r"\bspearhead(?:ed|s|ing)?\b",              'buzzword "spearhead" (use "led"/"built")'),
    (r"\butiliz(?:e|ed|es|ing)\b",               'weak verb "utilize" (use "use")'),
    (r"\bseamless(?:ly)?\b",                      'buzzword "seamless"'),
    (r"\brobust\b",                              'buzzword "robust"'),
    (r"\bsynerg\w*\b",                           'buzzword "synergy"'),
    (r"\bcutting[ -]edge\b",                      'cliche "cutting-edge"'),
    (r"\bbest[ -]in[ -]class\b",                  'cliche "best-in-class"'),
    (r"\bgame[ -]chang\w*\b",                     'cliche "game-changer"'),
    (r"\brevolutioniz\w*\b",                      'buzzword "revolutionize"'),
    (r"\bdelv(?:e|ed|es|ing)\b",                  'buzzword "delve"'),
    (r"\bmyriad\b",                              'buzzword "myriad"'),
    (r"\bplethora\b",                            'buzzword "plethora"'),
    (r"\bshowcas(?:e|ed|es|ing)\b",               'buzzword "showcase"'),
    (r"\bempower(?:ed|s|ing)?\b",                 'buzzword "empower"'),
    (r"\belevat(?:e|ed|es|ing)\b",               'buzzword "elevate"'),
    (r"\bharness(?:ing|ed)?\s+the\s+(?:power|potential)\b", 'cliche "harness the power"'),
    (r"\bmeticulous(?:ly)?\b",                    'cliche "meticulous"'),
    (r"\bpassionate\b",                          'cliche "passionate"'),
    (r"\bresults[ -]driven\b",                    'cliche "results-driven"'),
    (r"\bdetail[ -]oriented\b",                   'cliche "detail-oriented"'),
    (r"\bteam[ -]player\b",                       'cliche "team player"'),
    (r"\bself[ -]starter\b",                      'cliche "self-starter"'),
    (r"\bgo[ -]getter\b",                         'cliche "go-getter"'),
    (r"\badept\b",                              'cliche "adept"'),
    (r"\bproven track record\b",                 'cliche "proven track record"'),
    (r"\bhit the ground running\b",              'cliche "hit the ground running"'),
    (r"\bthink outside the box\b",               'cliche "think outside the box"'),
    (r"\bholistic\b",                           'buzzword "holistic"'),
    (r"\bpivotal\b",                            'inflated "pivotal"'),
    (r"\binstrumental\b",                       'inflated "instrumental"'),
    (r"\bfast[ -]paced\b",                       'cliche "fast-paced"'),
    (r"\bever[ -](?:evolving|changing)\b",       'cliche "ever-evolving"'),
    (r"\bat the forefront\b",                    'cliche "at the forefront"'),
    (r"\btestament to\b",                        'cliche "testament to"'),
    (r"\btapestry\b",                           'buzzword "tapestry"'),
    (r"\bwide (?:range|array) of\b",             'filler "wide range of"'),
    (r"\bwealth of\b",                          'filler "wealth of"'),
    (r"\bin today'?s\b",                         'cliche "in today\'s ..."'),
    (r"\bnavigat\w+ the (?:complexit|landscape)\w*\b", 'cliche "navigating the complexities"'),
    (r"\bplay(?:s|ed)? (?:a|an) (?:pivotal|key|crucial|central) role\b", 'cliche "played a key role"'),
    (r"\bnot just\b[^.\n]{0,60}\bbut\b",         '"not just X but Y" construction'),
    (r"\bnot only\b[^.\n]{0,60}\bbut\b",         '"not only X but Y" construction'),
]
BLOCK = [(re.compile(p, re.IGNORECASE), lab) for p, lab in _PATTERNS]
DASH_UNICODE = re.compile("[‒–—―]")   # figure/en/em/horizontal-bar
DOUBLE_HYPHEN = re.compile(r"-{2,}")                       # renders as en/em-dash in LaTeX


def is_target(path):
    """Resume .tex files only. Every resume tex path contains 'resume' (the
    resume/ dir, a resume-*.tex name, or data/resumes/), so this one check
    covers base variants, dream-target copies, the flat archive, and scratchpad
    working drafts -- while excluding jd.md, thread logs, and Resume-Facts.md."""
    p = path.replace("\\", "/").lower()
    return p.endswith(".tex") and "resume" in p


def strip_tex_comments(text):
    """Drop each line's LaTeX comment (unescaped % to end of line) so a note or
    the variant-header em-dash in a comment never trips the linter."""
    out = []
    for line in text.split("\n"):
        m = re.search(r"(?<!\\)%", line)
        out.append(line[:m.start()] if m else line)
    return "\n".join(out)


def changed_text(tool_input):
    """The text to lint: full content on Write, the added text on Edit/MultiEdit
    (never the pre-existing surrounding text, so unrelated edits don't trip)."""
    if tool_input.get("content") is not None:
        return tool_input["content"]
    if tool_input.get("new_string") is not None:
        return tool_input["new_string"]
    if isinstance(tool_input.get("edits"), list):
        return "\n".join(e.get("new_string", "") for e in tool_input["edits"])
    return ""


def detect(text, is_tex):
    scan = strip_tex_comments(text) if is_tex else text
    hits = []
    for rx, label in BLOCK:
        n = len(rx.findall(scan))
        if n:
            hits.append((label, n))
    n = len(DASH_UNICODE.findall(scan))
    if n:
        hits.append(("em/en dash: use commas, colons, or separate sentences (ASCII hyphen only on resumes)", n))
    if is_tex:
        n = len(DOUBLE_HYPHEN.findall(scan))
        if n:
            hits.append(('"--" renders as an en/em dash and extracts as a soft-hyphen (ATS-unsafe): use a single hyphen', n))
    return hits


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # fail open on unparseable payload
    if payload.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not is_target(path):
        return 0
    text = changed_text(tool_input)
    if not text.strip():
        return 0
    hits = detect(text, path.lower().endswith(".tex"))
    if not hits:
        return 0
    lines = ["voice-lint: AI-writing tells in %s (write blocked):" % os.path.basename(path)]
    for label, n in hits:
        lines.append("  - " + label + ((" x%d" % n) if n > 1 else ""))
    lines.append("Rewrite at the optimal resume register per resume/voice.md "
                 "(plain strong verbs, real specifics, tells stripped), then write the file again.")
    sys.stderr.write("\n".join(lines) + "\n")
    return 2  # block the write; stderr is fed back to the model


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # never let a linter bug wedge a write
