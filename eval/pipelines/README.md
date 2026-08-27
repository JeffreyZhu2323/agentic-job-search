# Eval pipelines

Automated (non-interactive) generators, so we can produce resume outputs at scale for E1-E4 without the
human review steps in the real skills.

## `run_tune.js` - the pipeline runner  (STATUS: untested, needs a shakedown run)
A Workflow script. Given one JD, it generates a **light** output (single-pass, mirrors `/tune-resume`)
and/or a **deep** output (diverge -> tournament -> refine, mirrors `/tune-resume-deep`), minus the
interactive reviews. Parameterized so the same runner serves every experiment.

**Invoke** via the Workflow tool (`scriptPath` = this file), with `args`:
```json
{
  "slug": "roblox-swe-intern",
  "jdPath": "C:/Users/jeffr/Desktop/Career/eval/jds/roblox-swe-intern.md",
  "mode": "both",
  "config": { "nDrafts": 4, "nJudges": 2, "genModel": "sonnet", "judgeModel": "sonnet" }
}
```

**Config knobs (map to the experiments):**
- `mode`: `light` | `deep` | `both` - E1 needs `both`.
- `nDrafts`: diverge count - **E3** varies this (e.g. 3 vs 6).
- `nJudges`: internal tournament judges - **E2** varies this (e.g. 1 vs 2).
- `genModel` / `judgeModel`: `sonnet` | `opus` - **E4** varies these. Default `sonnet` (cost).

**Outputs** land in `eval/outputs/`:
- `<slug>__light.{tex,pdf,txt}`
- `<slug>__deep.{tex,pdf,txt}` (+ `<slug>__deep_draft-<i>.tex` for the diverge drafts)

**Returns** `{ slug, mode, config, light, deep }` where each output carries `{ path, pages, ascii_clean,
title_ok, rendered }`.

### First-run checklist (validate before trusting results)
- [ ] Agents can write to `eval/outputs/` and compile with the TinyTeX `pdflatex` (PATH export is in the
      agent prompt).
- [ ] Each output is exactly one page, ASCII-clean, correct title (gate fields come back true).
- [ ] The deep tournament returns a sane winner and the refine step emits `<slug>__deep.tex`.
- [ ] Reuse-artifacts: the diverge drafts persist so **E3** can re-judge subsets without regenerating.

## Not built yet (next piece): the eval judge harness
`run_tune.js` only **generates** outputs. The **E1 comparator** - the 2-judge cross-tier blind panel
(Opus 4.8 + Sonnet 5), both-order + agreement rule from `DESIGN.md` - is a separate harness that takes two
output texts + the JD and returns a verdict. That plus the `keyword_coverage.py` sub-metric and result
aggregation are the remaining pieces to run E1.

Note: the runner's **internal** tournament (`nJudges`) is part of the *pipeline being evaluated* (what E2
studies); the **eval** judging (deep vs light) is the separate blind panel. Don't conflate them.
