# E0 — Do the closure dimensions aggregate to one scalar?

**Question:** Do grounding (G), rigidity (R), and preserved-ambiguity (P) collapse to ONE scalar latent factor — or must closure be represented as a multidimensional profile?

**Hypothesis:** [H-SCALAR](../../HYPOTHESES.md#h-scalar--grounding-rigidity-and-ambiguity-preservation-share-one-latent-factor). This experiment decides *scalar aggregation only* — whether the tests can be reported as a single closure score. It does **not** gate the program: the founding specification is multidimensional and typed (`C = (B, I, P, F, G, U, R, O)`), and whether a structured specification exists is tested separately by E4–E7. Under the governing rule, this experiment may directly retire only the claim it measures.

## Status and prior art

`OPEN`. The statistical instrument — exploratory factor analysis with parallel analysis over score matrices — was validated on LLM *capability* benchmarks (arXiv:2507.20208: 60 models × 44 benchmarks, low-rank latent structure found). Nobody has applied it to structural-*quality* axes. The one candidate pre-emption (arXiv:2605.08522) was **withdrawn by its authors** (May 2026) citing a fatal flaw, and asserted orthogonality by construction rather than testing for collapse. Motivational neighbor: construct-validity critiques of LLM benchmarks (arXiv:2511.04703). Citation statuses: [VERIFICATION.md](../../VERIFICATION.md).

## Protocol

1. **Assemble the task battery.** 100–200 tasks across at least three families (retrieval-grounded QA, multi-source reasoning, open-ended analysis), each admitting all three measurements on its output. Record per-task difficulty covariates (source count, length, task family).
2. **Generate outputs.** One fixed model (then optionally replicate across 2–3 models). Structured output so claims are pre-decomposed at generation time (avoids post-hoc claim-splitting circularity).
3. **Score G** — leave-one-out causal grounding: remove each source, regenerate K≥3 times, compare claims via bidirectional NLI entailment (DeBERTa-large-MNLI class of classifier — not cosine similarity). Per-claim score in [0,1], aggregate per output.
4. **Score R** — rigidity: paraphrase the input N=5 ways (an LLM generates the paraphrases — tool, not judge), NLI-compare conclusion stability. Per-conclusion score in [0,1], aggregate.
5. **Score P** — preserved ambiguity: N=10 generations, embedding/NLI clustering, dispersion score.
6. **Indicator design — three indicators are not enough.** With p = 3, a one-factor model is just-identified and one- vs two-factor structure is not testable; "shared variance on one factor" would nearly restate "the three correlations are positive and similar." Therefore G, R and P are each decomposed into sub-indicators: G → [mean per-claim grounding, minimum grounding, fraction of decorative claims]; R → [mean conclusion stability, worst-case stability]; P → [cluster count, dispersion]. Seven indicators, over which one- vs multi-factor structure is genuinely identifiable.
7. **Fit** exploratory factor analysis + parallel analysis over the sub-indicator matrix (retention by Horn's parallel analysis, not eigenvalue > 1). Compare a one-latent model against multi-factor alternatives. Report explained shared variance and loadings.
8. **Confound control.** Partial out output length and task difficulty. A shared "hard task" factor can masquerade as a shared "closure" factor — if the single factor vanishes after controlling for difficulty, that is a disproof, not a nuisance.

## Verdict conditions (pre-registered)

- **SCALAR CLOSURE HOLDS** iff a single latent factor explains **≥ 60% of shared variance** across the sub-indicator battery AND all sub-indicators load on it with the same sign, surviving the difficulty control — the tests may be aggregated into one closure score.
- **SCALAR CLOSURE IS A METAPHOR** iff pairwise |r| < 0.2 and no factor clears the parallel-analysis threshold — the single aggregate score is retired and closure is reported as a multidimensional profile.
- Anything between: report the structure found; partial-collapse (e.g., G+R share a factor, P doesn't) is a meaningful, publishable answer that reshapes the concept.

**Scope of the verdict.** This experiment decides scalar aggregation only. A metaphor result retires the single closure score and the one-dimensionality claim — **and nothing else**. It does not retire the operators (E4, E5), composition (E7), lowering / the IR (E6), or any of the measurements; factor analysis has no power over whether a structured specification exists. The independent structural hypotheses remain logically open ([consequence matrix](../../HYPOTHESES.md#consequence-matrix)).

## Cost and prerequisites

API credits for generation + scoring (the K and N multipliers dominate); a CPU is enough for the NLI classifier and the factor analysis. No GPU training. Days of work.

## Exclusion criteria (pre-registered)

Excluded before analysis, counted and reported: outputs failing structured-output parsing; tasks where any of G/R/P cannot be scored (e.g., zero extractable claims), with reason logged. Never excluded: any item based on its score values — outcome-based exclusion is the confound this design exists to avoid.

## Wanted from contributors

- The scoring harness (G/R/P as clean, reusable functions — this is the program's shared instrument).
- Task battery curation (diverse, difficulty-annotated).
- The factor-analysis notebook with the pre-registered decision rule implemented before scores exist.
