# Eval Harness - Operational Design

Concrete design for the experiments specified in `README.md`. Decisions made 2026-08-15; revisit if E1
comes out borderline. Principles: comparative (pairwise) judging, model held constant *within* a
comparison, deterministic checks where a script can do the job, LLM judgment only where it can't.

---

## 1. Judge panel + rubric

### Panel: 2 judges, cross-tier
- **Opus 4.8 + Sonnet 5** - two tiers to blunt one model's idiosyncratic taste and self-preference bias
  while keeping labels reliable. (Haiku dropped: too weak for nuanced resume comparison, not worth the
  noisy label.)
- Judges are **never the same instance as the generators**, and see **no pipeline labels** (blind: "Resume
  A" / "Resume B" only).
- Each comparison is run in **both orders** (A,B) and (B,A) per judge.

### Per-judge vote rule (order-bias control)
Each judge votes in both orders. **Consistent pick across both orders -> that judge's vote. Flips on swap
-> that judge ABSTAINS** (contributes toward a tie). This bakes position-bias defense into the vote.

### Rubric dimensions (recruiting lens, from CLAUDE.md)
1. **ATS / keyword pass** - surfaces the JD's must-have, *truthfully-backed* keywords.
2. **6-second scan** - top third lands the right positioning + strongest impact instantly.
3. **Hiring-manager credibility** - concrete and credible, no fluff or overclaim.
4. **JD fit / positioning** - aimed at THIS role, not generic.
5. **Human + tight** - no buzzword tells (leveraged/spearheaded/robust/seamless), no formulaic
   parallelism, no dash-as-connector, one page.

### Exact judge prompt (verbatim)
```
You are an expert technical recruiter and hiring manager screening resumes for the role below.
Two resumes for the same candidate are shown, A and B. Decide which is STRONGER for THIS role.

JOB DESCRIPTION:
<jd>

RESUME A:
<resume_a>

RESUME B:
<resume_b>

Judge on: (1) ATS/keyword pass - surfaces the JD's must-have keywords the candidate can truthfully
claim; (2) 6-second recruiter scan - top third instantly lands the right positioning and strongest
impact; (3) hiring-manager credibility - concrete and credible, no fluff or overclaim; (4) JD fit -
aimed at this specific role, not generic; (5) human and tight - no buzzword tells, no formulaic
parallelism, one page.

Do NOT assign numeric scores. Output exactly:
VERDICT: A | B | TIE
REASON: <two sentences max>
```

---

## 2. E3 distinctness metric

No local embedding source, so **LLM-rated strategic distinctness is primary** (the thing that matters is
*positioning* divergence, which n-gram similarity misses).
- For each pair of drafts, a judge rates **1-5**: 1 = same angle reworded, 5 = a genuinely different
  strategic bet. Mean over all pairs = the batch's diversity.
- **Deterministic sanity check** (no embeddings needed): **Jaccard similarity on bullet n-grams** between
  drafts, to catch cosmetic near-duplicates an LLM might over-rate as "distinct."
- **E3's decision is driven by the ablation, not the distinctness number:** does the tournament winner
  among 6 drafts differ from the winner among a random 3, across JDs? Distinctness is diagnostic (are we
  buying real diversity or cosmetic variants?).

### Distinctness prompt (verbatim)
```
Two resume drafts for the same candidate and role are shown. Rate how strategically DISTINCT their
positioning/angle is, ignoring wording polish. 1 = essentially the same angle reworded; 5 = a clearly
different strategic bet (e.g. SWE-first vs AI-first, impact-led vs research-led).

DRAFT A:
<draft_a>
DRAFT B:
<draft_b>

Output only: DISTINCTNESS: <1-5>
```

---

## 3. Keyword-coverage script (deterministic sub-metric)

Objective keyword coverage, no preference judgment. The denominator is **truthfully-claimable** keywords
(JD ∩ Resume-Facts), so we never reward stuffing terms Jeffrey can't back.

### Keyword spec (per JD)
Each JD gets a companion `eval/jds/<slug>.keywords.tsv`, one keyword per line:
```
<term>	<claimable|gap>	<alias1;alias2;...>
```
- `claimable` = a JD must-have that IS in `resume/Resume-Facts.md` (can truthfully claim).
- `gap` = a JD must-have NOT in Resume-Facts (must NOT appear on the page).
- aliases = surface forms that count as a match (e.g. term `LLMs`, aliases `large language models;LLM`).
- Bootstrapped by an LLM proposing JD keywords tagged against Resume-Facts, then **locked by hand** once
  per JD (extraction is reliable, but the claimable/gap tag is the honesty boundary, so a human confirms).

### Script: `eval/scripts/keyword_coverage.py` (stdlib Python)
- Input: resume PDF (or its `pdftotext` output) + the JD's keyword spec.
- Normalize resume text: lowercase, collapse whitespace.
- A `claimable` term is **present** if the term or any alias appears (normalized substring match).
- Output:
  - `coverage_pct` = claimable-present / claimable-total
  - `missing` = claimable terms absent
  - `gap_leakage` = `gap` terms that appeared -> should be empty; **nonzero is a truthfulness red flag**
    (possible fabrication), reported loudly.

---

## 4. Result aggregation

### Per pair (one JD: deep vs light)
2 judges x 2 orders -> each judge votes or abstains (order-bias rule). **Pair outcome = unanimous
agreement among the non-abstaining judges, with at least one non-abstainer:** both agree -> that resume
wins; they split, or both abstain -> **TIE**; one abstains and the other votes -> the voting judge decides
(flagged as a single-judge call). Abstention is rare and signals a genuine toss-up, so leaning tie there
is correct.

### E1 (deep vs light) across the JD set
- **Deep W-L-T** across JDs, and **win-rate = wins / (wins + losses)** (ties excluded from the ratio,
  reported separately).
- **Per-JD-type breakdown** (AI-heavy / ML-DS / generalist-with-AI / borderline): win-rate within each
  type - this is the routing-rule signal (does deep only win on ambiguous cases?).
- Per output, alongside: **keyword coverage %** and **gap leakage**, deep vs light (does deep improve
  coverage or just polish wording?).
- **Cost:** log tokens per pipeline per JD; headline metric is **quality-per-token**, not quality alone.
- **Thresholds:** win-rate <60% -> collapse toward light + 1 critic; >75% -> keep and optimize internals;
  in between -> let the per-type breakdown decide a routing rule.

### E2 (judge variance)
- Fix one draft set; single-judge round-robin repeated 8-10x.
- Report **winner-flip rate** across reruns, **Kendall's tau** vs the modal ranking, and **position-bias**
  (fraction of pairwise judgments that flip on order swap, per tier).
- Decision: single-judge winner matches the 2-judge panel result >~90% with low flip -> drop to 1 judge
  (with order-randomization); else keep the 2-judge panel.

### E3 (draft count)
- **Winner-consistency:** fraction of JDs where the full-6 winner == a random-3-subset winner.
- **Mean pairwise distinctness** (LLM 1-5) + Jaccard sanity check.
- Decision: winner stable at 3 -> cap drafts at 3-4.

### E4 (model tier)
- Deep-vs-light with generation on Sonnet vs Opus, judged blind. Also the **Opus spot-check** that must
  pass before any design change derived from Sonnet-only data is committed.
- Decision: Opus not detectably better at a stage -> tier that stage to Sonnet.

### Results storage (`eval/results/`)
- `e1_pairs.tsv` - one row per (JD, judge, order): verdict + reason.
- `e1_summary.md` - the W-L-T table, per-type breakdown, coverage %, cost, quality-per-token.
- Analogous files per experiment. **Keep raw judge outputs** so every result is auditable.
