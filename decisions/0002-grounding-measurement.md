# 0002 — Grounding (G): leave-one-out, NLI scalar, aggregators, decorative claims

- Status: proposed
- Deciders: closure research program contributors
- Scope: E0 (two of its seven sub-indicators), E5 (contamination detector reuses this machinery)

## Context
E0's protocol names grounding as "leave-one-out causal grounding … compare claims via bidirectional NLI
entailment (DeBERTa-large-MNLI class — not cosine)" and names three of its sub-indicators (mean grounding,
minimum grounding, fraction of decorative claims). It does not give the NLI checkpoint, the per-claim scalar, the
leave-one-out contrast, the aggregators, or the definition of "decorative." Each changes a sub-indicator value.

## Decision
- **NLI checkpoint:** `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` (pin the revision hash). This is
  the current member of the DeBERTa-MNLI family the protocol names — trained on five combined NLI datasets, the
  hard-example upgrade over the 2021 MNLI-only checkpoints. CPU-lighter fallback:
  `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`.
- **Per-claim scalar:** `P(entail | premise = concatenated retained sources, hypothesis = claim) −
  P(contradict)`, mapped to `[0,1]` via `(s+1)/2`; take the maximum over individual source premises when
  multi-source; "bidirectional" = also run premise/hypothesis swapped and average the two directions.
- **Leave-one-out contrast:** `grounding_drop(claim, s) = scalar(full sources) − mean over K of scalar(sources ∖
  s)`; a claim depends on source `s` iff the drop ≥ **0.15**. This threshold is **not a bare constant** — it is
  calibrated on a held-out slice before freeze, or pre-registered together with a sensitivity sweep over
  {0.10, 0.15, 0.20} reporting verdict stability.
- **Aggregators (both, as separate sub-indicators):** `mean_grounding` = arithmetic mean of the per-claim scalar
  over the claim list; `min_grounding` = its minimum. An empty claim list yields NaN and the row is excluded and
  logged — never silently scored as 0.
- **Decorative claim:** *structural* — a claim is decorative iff its `source_ids` is empty. `fraction_decorative`
  = decorative claims / total. Structural is chosen over a score-threshold definition precisely because it has no
  tunable cutoff to fish.
- **K:** 5 regenerations (satisfies the protocol's K ≥ 3 floor; matches R's N).

## Consequences
Defines exactly what "grounding" means as a number, so two of E0's seven sub-indicators are reproducible, and
E5's contamination detector (0007) can reuse the same contrast. The 0.15 dependence cutoff is the single most
result-sensitive value here and carries an explicit anti-fishing requirement.
