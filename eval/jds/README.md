# JD test set

One file per JD (raw posting text; strip only pure legal/EEO boilerplate). Span role types so the eval
generalizes rather than overfitting to one kind of posting. Target ~6-8 total.

## Coverage checklist (fill the slots)
- [x] **Generalist-SWE-with-AI** - `roblox-swe-intern.md` (the ambiguous-positioning case: SWE-first vs AI-first)
- [ ] **AI-heavy** (Applied AI / LLM / Agent Engineer) - clear fit for the `ai` variant
- [ ] **ML/DS** (MLE / Data Scientist / Research Engineer) - clear fit for the `mlds` variant
- [ ] **AI-heavy #2** or **ML/DS #2** - a second in whichever is your densest target pool
- [ ] **Borderline / poor-fit** (heavy on skills Jeffrey lacks, e.g. distributed systems or pure frontend)
      - tests whether deep tune helps or just polishes a bad fit
- [ ] (optional) 1-2 more real postings you'd actually apply to

Why the spread: E1's key secondary signal is *which JD types the deep tune wins on*. If it only wins on
ambiguous cases like Roblox and ties on clear-fit ones, the right answer is a routing rule, not a cheaper
pipeline. That signal only appears if the set spans types.
