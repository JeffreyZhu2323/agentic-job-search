# Resume-Tune Eval Harness

**Purpose:** measure, with data instead of intuition, (1) whether `/tune-resume-deep` actually earns its
~3-5x token cost over `/tune-resume`, and (2) how to right-size the deep tune's internals (judge count,
draft count, model tier). Feeds FEATURE-PLAN P4.

**Core caveat (read first):** judging is **LLM-panel only** (no human labels, by choice). The quality
signal is therefore a **proxy**: LLM *preference*, not real callback/interview rate. Without a human
anchor the risk sharpens to measuring "what LLM judges like" rather than "what recruiters respond to." We
harden against it structurally instead of relying on a human:
- **Rubric-anchored judging** - judges score against a concrete recruiting rubric (ATS keyword coverage,
  6-second-scan positioning, hiring-manager credibility, JD-fit), not a vague "which is better."
- **Deterministic sub-metrics** - keyword-coverage %, one-page, ATS-parse-safety are measured by script,
  not preference; these partly escape the proxy problem and give an objective backbone.
- **Generator != judge + cross-tier panel** - judge models differ from the generators, and the panel
  mixes tiers (e.g. Opus + Sonnet) to blunt single-model idiosyncratic taste and self-preference bias.
- **Order-bias control** - every pairwise comparison runs in **both** A/B orders; a judge that flips on
  swap is scored a **tie**, not a win.
Don't chase proxy gains past the point of plausible real-world effect. (Jeffrey does not judge individual
resumes; he makes the final design call from the aggregate metrics.)

---

**Operational design** (judge panel + exact rubric prompt, E3 metric, keyword-coverage script,
result aggregation): see `eval/DESIGN.md`.

## Directory layout
- `jds/` — the JD test set (input). One file per JD. **Span role types** so results generalize:
  AI-heavy, ML/DS, generalist-SWE-with-AI, and borderline/poor-fit. Target ~6-8 JDs.
- `outputs/` — generated resumes per JD per pipeline (and per ablation variant).
  Naming: `<jd-slug>__<pipeline>[__<variant>].{tex,pdf,txt}` (e.g. `roblox__deep.pdf`, `roblox__light.pdf`).
- `results/` — blind A/B judgments, variance/diversity metrics, and summary tables.

## Controls (hold constant so we measure tuning, not inputs)
- All outputs build from the **same** `resume/Resume-Facts.md` and the same base variant selection logic.
- Blind comparison: strip identifiers; run **both A/B orders** and score a flip-on-swap as a tie.
- Labels: **independent LLM judge panel only** (no human judging). 2-judge cross-tier panel (Opus 4.8 +
  Sonnet 5); generators excluded from judging their own outputs; both-order + agreement rule;
  rubric-anchored. Full rule in `DESIGN.md`.

---

## Experiments (ordered by information value)

### E1 - Meta: deep vs light (is the whole apparatus worth it?)
For each JD, produce a `/tune-resume` output and a `/tune-resume-deep` output. Blind pairwise: which is
stronger for this JD?
- **Metric:** deep-tune win-rate across the JD set (plus per-JD-type breakdown).
- **Decision:** <60% -> not earning its cost; collapse toward light + 1 critic. >75% -> justified, optimize
  internals. In between -> look at *which* JD types deep wins on.
- **Key secondary signal:** if deep only wins on **ambiguous-positioning** JDs (like Roblox: SWE-vs-AI
  framing) and ties on clear-fit JDs, the answer isn't "cheaper" - it's a **routing rule** that fires the
  deep tune only on hard cases.

### E2 - Judge variance (how many judges?)
Fix one draft set. Run a single-judge round-robin 8-10 times; run the 3-judge majority the same way.
- **Metric:** winner-flip rate and Kendall's tau vs the modal winner; plus a **position-bias check**
  (run each pair in both A/B orders, flip-rate = bias magnitude).
- **Decision:** single-judge winner matches the 2-judge panel result >~90% with low flips -> drop to 1
  judge (with order-randomization). Otherwise keep the 2-judge panel.

### E3 - Draft count / real diversity (how many drafts?)
Generate 6 drafts; score pairwise distinctness (embedding cosine or an LLM 1-5 rating).
- **Metric:** does the tournament winner among 6 differ from the winner among a random 3, across JDs?
- **Decision:** winner stable at 3 -> cap drafts at 3-4.

### E4 - Model tier (Opus vs Sonnet where?)
Generate drafts on Sonnet vs Opus; blind-judge whether Opus drafts are detectably better. Repeat for the
judge role.
- **Decision:** not detectably better -> tier that stage down to Sonnet (likely quality-neutral savings).

---

## Status / next steps
- [ ] Assemble the JD set in `jds/` (~6-8 spanning role types). Seed: the Roblox JD already exists at
      `companies/roblox/jd.md` - copy the raw posting in as the first.
- [ ] Generate outputs (light + deep) for the JD set into `outputs/`.
- [ ] Run **E1** (meta deep-vs-light) - this gates everything; if deep isn't worth it, E2-E4 are moot.
- [ ] Run E2 / E3 / E4 to right-size internals (only if E1 says keep deep).
- [ ] Decide final design; update `tune-resume-deep` and FEATURE-PLAN P4 with the data.

## Notes
- Small n (~6-8 JDs) is directional, not publication-grade; sufficient for a personal tool.
- Track token cost per pipeline per run alongside quality, so "worth it" is quality **per token**, not
  quality alone.
