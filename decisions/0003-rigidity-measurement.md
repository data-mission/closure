# 0003 — Rigidity (R): paraphrase generation, validity gate, stability scalar

- Status: proposed
- Deciders: closure research program contributors
- Scope: E0 (two of its seven sub-indicators)

## Context
E0's protocol names rigidity as "paraphrase the input N=5 ways (an LLM generates the paraphrases — tool, not
judge), NLI-compare conclusion stability" and names two sub-indicators (mean conclusion stability, worst-case
stability). It leaves open which model paraphrases, whether paraphrases are validated, the stability formula, and
the aggregators.

## Decision
- **Paraphraser:** a *separate* pinned model from the generation model in 0001 (different family), temperature
  0.7, N = 5 paraphrases, prompt: "rewrite preserving exact meaning and answerable content." A different family
  avoids the confound where the generator's own biases seed the paraphrases it is then tested against.
- **Validity gate:** accept a paraphrase only if bidirectional NLI entailment between original and paraphrase ≥
  **0.85** in both directions; otherwise resample (up to 10 tries, then drop and log). Without this, a
  meaning-changing paraphrase makes R measure "the question changed," not model rigidity.
- **Stability scalar:** for a conclusion set `{c0 = baseline, c1..c5 = paraphrase-conditioned}`, each `ci` (i ≥ 1)
  versus `c0` gives a symmetric NLI agreement (both directions, entail − contradict → [0,1]); stability = the mean
  of the five each-versus-baseline agreements. Anchoring to the un-paraphrased baseline (rather than all-pairs) is
  the natural reference point.
- **Aggregators (both, as separate sub-indicators):** `mean_conclusion_stability` = mean across the row's
  conclusions; `worst_case_stability` = minimum. A single-conclusion row sets both equal to that conclusion's
  stability.

## Consequences
Defines R as a number for two of E0's seven sub-indicators. The 0.85 paraphrase-validity gate is the
result-sensitive value here; like 0002's cutoff it is frozen before data. Choosing a different-family paraphraser
is a deliberate cost (a second model) paid to remove a real confound.
