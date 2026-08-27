export const meta = {
  name: 'eval-run-tune',
  description: 'Generate light and/or deep tuned resumes for one JD, non-interactively, for the eval harness',
  phases: [
    { title: 'Light' },
    { title: 'Diverge' },
    { title: 'Tournament' },
    { title: 'Refine' },
  ],
}

// ---------------------------------------------------------------------------
// Automated (non-interactive) resume-tune pipeline runner for the eval harness.
// Mirrors /tune-resume (light) and /tune-resume-deep (deep) WITHOUT the human
// review steps, so we can generate outputs at scale for E1-E4.
//
// Invoke via the Workflow tool with args, e.g.:
//   { "slug": "roblox-swe-intern",
//     "jdPath": "C:/Users/jeffr/Desktop/Career/eval/jds/roblox-swe-intern.md",
//     "mode": "both",
//     "config": { "nDrafts": 4, "nJudges": 2, "genModel": "sonnet", "judgeModel": "sonnet" } }
//
// Outputs land in eval/outputs/ as <slug>__light.{tex,pdf} and <slug>__deep.{tex,pdf}
// (deep drafts: <slug>__deep_draft-<i>.tex). Returns paths + gate results per output.
//
// STATUS: untested. Needs one shakedown run to validate agent file-IO/compile and
// the winner aggregation before it is trusted for real eval data.
// ---------------------------------------------------------------------------

const A = args || {}
const ROOT = 'C:/Users/jeffr/Desktop/Career'
const slug = A.slug || 'jd'
const jdPath = A.jdPath || `${ROOT}/eval/jds/${slug}.md`
const factsPath = A.factsPath || `${ROOT}/resume/Resume-Facts.md`
const baseAiPath = A.baseAiPath || `${ROOT}/resume/resume-ai.tex`
const baseMlPath = A.baseMlPath || `${ROOT}/resume/resume-mlds.tex`
const outDir = A.outDir || `${ROOT}/eval/outputs`
const mode = A.mode || 'both'            // 'light' | 'deep' | 'both'
const cfg = A.config || {}
const nDrafts = cfg.nDrafts || 4
const nJudges = cfg.nJudges || 2
const genModel = cfg.genModel || 'sonnet'
const judgeModel = cfg.judgeModel || 'sonnet'

const ANGLES = [
  'agentic / LLM-systems engineering (make the multi-agent orchestrator the centerpiece)',
  'production software-engineering ownership: build, test, ship to production',
  'impact / scale / metrics first (every bullet opens with a quantified result)',
  'maximize truthful JD-keyword alignment (no stuffing, no fabrication)',
  'ML / research depth',
  'experimentation / investigative engineer (benchmarks, evals, ablations)',
]

// Shared rules every generation agent must follow.
const RULES = `
Read the JD at ${jdPath}, the truthful fact inventory at ${factsPath}, and the closer base
variant (AI: ${baseAiPath} for AI/LLM/agent roles; ML/DS: ${baseMlPath} for MLE/DS roles).
HARD RULES:
- Draw claims ONLY from Resume-Facts.md CAN CLAIM. Never fabricate. Surface nothing unconfirmed.
- One page. ASCII only (no en/em-dash, no math arrows -> write "to"; $\\sim$ ok for approx).
- Job title EXACTLY: Software Engineer Intern - AI Agents
- Keep the base template macros/preamble, single column, grouped plaintext skills, \\textbullet items.
- Hold the dials: technical but legible to a non-engineer recruiter; human (no buzzword tells -
  leveraged/spearheaded/robust/seamless, no formulaic parallelism, no dash-as-connector); tight.
COMPILE (run in the output dir):
  export PATH="$PATH:/c/Users/jeffr/AppData/Roaming/TinyTeX/bin/windows"
  pdflatex -interaction=nonstopmode -halt-on-error <file>.tex
  pdftotext <file>.pdf <file>.txt
Verify the log says "Output written on ... (1 page" and the extracted text is clean ASCII.
Return: path (the .tex), pages (integer from the log), ascii_clean, title_ok, and rendered (the pdftotext text).`

const GATE_SCHEMA = {
  type: 'object',
  properties: {
    path: { type: 'string' },
    pages: { type: 'integer' },
    ascii_clean: { type: 'boolean' },
    title_ok: { type: 'boolean' },
    rendered: { type: 'string' },
  },
  required: ['path', 'pages', 'rendered'],
}

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    winner: { type: 'integer' },
    runnerUp: { type: 'integer' },
    reason: { type: 'string' },
  },
  required: ['winner', 'reason'],
}

function lightPrompt() {
  return `Produce a SINGLE-PASS JD-tailored one-page resume (mirrors /tune-resume; no review loop).
${RULES}
Write the final .tex to ${outDir}/${slug}__light.tex, then compile and verify as above.`
}

function divergePrompt(angle, i) {
  return `Produce ONE full tuned resume draft from the chosen base variant, with this DISTINCT angle:
${angle}.
${RULES}
Write the .tex to ${outDir}/${slug}__deep_draft-${i}.tex, then compile and verify as above.`
}

function judgePrompt(drafts) {
  const blocks = drafts.map(x => `--- DRAFT ${x.i} ---\n${x.d.rendered}`).join('\n\n')
  return `You are an expert technical recruiter + hiring manager. Below are ${drafts.length} resume
drafts (by index) for the same candidate, tuned for the JD at ${jdPath} (read it).
Run a pairwise round-robin comparing them on: ATS/keyword pass (truthful), 6-second recruiter scan,
hiring-manager credibility, JD fit, and human+tight (no buzzword tells, one page). Do NOT use numeric
scores; reason pairwise. Pick the single strongest WHOLE draft.
Return winner = its index, runnerUp = second-best index, reason = 2 sentences.

DRAFTS:
${blocks}`
}

function refinePrompt(winnerIdx, drafts) {
  const win = drafts.find(x => x.i === winnerIdx) || drafts[0]
  return `Refine the winning draft into the final deep-tune output. Read the winning draft at
${win.d.path}. Apply ONE critic pass (over-fit/pandering guard + hiring-manager credibility): cut any
forced JD-echo or buzzword tell, front-load the strongest result, keep it a coherent one page. Do not
add any claim not in ${factsPath}.
${RULES}
Write the final .tex to ${outDir}/${slug}__deep.tex, then compile and verify as above.`
}

function pickMode(votes, fallback) {
  const counts = {}
  for (const v of votes) counts[v] = (counts[v] || 0) + 1
  let best = fallback, bestN = 0
  for (const k of Object.keys(counts)) {
    if (counts[k] > bestN) { bestN = counts[k]; best = Number(k) }
  }
  return best
}

// -------------------------- run --------------------------
let light = null
if (mode === 'light' || mode === 'both') {
  phase('Light')
  light = await agent(lightPrompt(), {
    label: `light:${slug}`, phase: 'Light', schema: GATE_SCHEMA,
    model: genModel, agentType: 'general-purpose',
  })
}

let deep = null
if (mode === 'deep' || mode === 'both') {
  phase('Diverge')
  const angles = ANGLES.slice(0, nDrafts)
  const raw = await parallel(angles.map((ang, i) => () =>
    agent(divergePrompt(ang, i), {
      label: `draft-${i}:${slug}`, phase: 'Diverge', schema: GATE_SCHEMA,
      model: genModel, agentType: 'general-purpose',
    })
  ))
  const drafts = raw.map((d, i) => ({ d, i })).filter(x => x.d && x.d.rendered)
  if (drafts.length === 0) {
    log('Diverge produced no usable drafts; aborting deep.')
  } else {
    phase('Tournament')
    const judged = await parallel(Array.from({ length: nJudges }, (_, j) => () =>
      agent(judgePrompt(drafts), {
        label: `judge-${j}:${slug}`, phase: 'Tournament', schema: JUDGE_SCHEMA,
        model: judgeModel, agentType: 'general-purpose',
      })
    ))
    const votes = judged.filter(Boolean).map(v => v.winner)
    const winnerIdx = votes.length ? pickMode(votes, drafts[0].i) : drafts[0].i
    log(`Deep winner: draft ${winnerIdx} (judge votes: ${JSON.stringify(votes)})`)
    phase('Refine')
    deep = await agent(refinePrompt(winnerIdx, drafts), {
      label: `refine:${slug}`, phase: 'Refine', schema: GATE_SCHEMA,
      model: genModel, agentType: 'general-purpose',
    })
  }
}

return { slug, mode, config: { nDrafts, nJudges, genModel, judgeModel }, light, deep }
