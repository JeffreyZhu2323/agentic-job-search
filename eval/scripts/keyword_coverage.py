#!/usr/bin/env python3
"""Deterministic keyword-coverage sub-metric for the resume-tune eval harness.

Measures, for one resume against one JD's keyword spec:
  - coverage_pct : fraction of TRUTHFULLY-CLAIMABLE JD keywords present on the page
  - missing      : claimable keywords absent
  - gap_leakage  : `gap` keywords (JD wants them, Jeffrey CANNOT claim) that appeared
                   -> should always be empty; nonzero is a truthfulness red flag (possible fabrication)

Denominator is claimable-only by design, so stuffing terms he can't back never inflates the score.
See eval/DESIGN.md section 3.

Keyword spec format (TSV, one keyword per line; blank lines and #-comments ignored):
    <term>\t<claimable|gap>\t<alias1;alias2;...>
The alias column is optional. A term counts as present if the term OR any alias matches.

Usage:
    python keyword_coverage.py <resume.pdf|resume.txt> <spec.tsv> [--json]

PDFs are extracted via `pdftotext` (must be on PATH). Matching is case-insensitive, whitespace-normalized
(so multi-word terms match across line wraps), with word-ish boundaries so "Python" does not match
"Pythonic".
"""
import sys
import re
import json
import subprocess


def load_text(path):
    """Return normalized resume text from a .pdf (via pdftotext) or a text file."""
    if path.lower().endswith(".pdf"):
        try:
            out = subprocess.run(
                ["pdftotext", path, "-"],
                capture_output=True, text=True, check=True,
            )
            raw = out.stdout
        except FileNotFoundError:
            sys.exit("ERROR: pdftotext not found on PATH. Install poppler, or pass an extracted .txt.")
        except subprocess.CalledProcessError as e:
            sys.exit(f"ERROR: pdftotext failed on {path}: {e.stderr.strip()}")
    else:
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    # normalize: lowercase, collapse all whitespace runs (incl. newlines) to single spaces
    return re.sub(r"\s+", " ", raw.lower()).strip()


def parse_spec(path):
    """Return list of (term, tag, [aliases]) from the TSV spec."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            term = parts[0].strip()
            tag = parts[1].strip().lower() if len(parts) > 1 else ""
            aliases = []
            if len(parts) > 2 and parts[2].strip():
                aliases = [a.strip() for a in parts[2].split(";") if a.strip()]
            if tag not in ("claimable", "gap"):
                sys.exit(f"ERROR: {path}:{lineno}: tag must be 'claimable' or 'gap', got {tag!r}")
            rows.append((term, tag, aliases))
    return rows


def present(term, text):
    """True if the normalized term appears in text with word-ish boundaries."""
    norm = re.sub(r"\s+", " ", term.lower()).strip()
    if not norm:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(norm) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def matches_any(term, aliases, text):
    return present(term, text) or any(present(a, text) for a in aliases)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv[1:]
    if len(args) != 2:
        sys.exit("Usage: python keyword_coverage.py <resume.pdf|resume.txt> <spec.tsv> [--json]")
    resume_path, spec_path = args
    text = load_text(resume_path)
    spec = parse_spec(spec_path)

    claimable = [(t, al) for (t, tag, al) in spec if tag == "claimable"]
    gaps = [(t, al) for (t, tag, al) in spec if tag == "gap"]

    present_claim = [t for (t, al) in claimable if matches_any(t, al, text)]
    missing = [t for (t, al) in claimable if not matches_any(t, al, text)]
    gap_leak = [t for (t, al) in gaps if matches_any(t, al, text)]

    total = len(claimable)
    coverage_pct = round(100.0 * len(present_claim) / total, 1) if total else 0.0

    result = {
        "resume": resume_path,
        "spec": spec_path,
        "claimable_total": total,
        "claimable_present": len(present_claim),
        "coverage_pct": coverage_pct,
        "missing": missing,
        "gap_leakage": gap_leak,
    }

    if as_json:
        print(json.dumps(result, indent=2))
        return

    print(f"resume : {resume_path}")
    print(f"spec   : {spec_path}")
    print(f"coverage: {len(present_claim)}/{total} claimable keywords present ({coverage_pct}%)")
    if missing:
        print("missing (claimable, absent):")
        for t in missing:
            print(f"  - {t}")
    else:
        print("missing: none")
    if gap_leak:
        print("!! GAP LEAKAGE (JD terms Jeffrey CANNOT claim, but present -> truthfulness red flag):")
        for t in gap_leak:
            print(f"  !! {t}")
    else:
        print("gap leakage: none (clean)")


if __name__ == "__main__":
    main()
