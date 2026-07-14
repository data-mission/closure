# E7 — Composition

**Question:** Do composed checks — grounding results feeding ambiguity checking feeding collapse detection — catch real failures that no individual check catches?

**Hypothesis:** [H-COMPOSE](../../HYPOTHESES.md#h-compose--composed-checks-catch-what-isolated-checks-miss). Not gated on E0 — whether the tests aggregate to one score (E0) and whether *composing* them adds detection power (this) are separate questions. A failure retires the compositional algebra at this level; independent instruments remain useful.

## Status

`OPEN` — designed in the program's earlier phase, never run. Distinct from E0: E0 asks whether one *object* underlies the measurements (shared variance); E7 asks whether *pipelining* them adds detection power (incremental catches). The two can dissociate — correlated readouts can still have non-overlapping blind spots, and independent readouts can still compose usefully. Interpret E7's result in light of E0's.

## Design

Three adversarial task types, 10–20 tasks each, constructed so that single checks are expected to pass while the composition is expected to catch the failure:

- **Type A — conflicting sources + memorized answer.** The model has strong parametric knowledge; provided sources disagree with it and with each other. Target failure: decorative citations that pass grounding in isolation. Pipeline: G identifies weakly-grounded claims → P checks whether uncertainty about *those specific claims* survives into the output.
- **Type B — ambiguous question + dominant framing.** One interpretation is far more common in training data. Target failure: false synthesis that blends interpretations fluently. Pipeline: P identifies distinct positions → collapse detection checks whether they were merged.
- **Type C — multi-source with outlier.** One source contradicts the consensus of the others. Target failure: consensus absorption — the outlier silently disappears. Pipeline: G per-source dependence → P cluster structure over the outlier's claim.

## Protocol

1. Build the three task sets with known, human-adjudicated target failures.
2. Run each individual check alone; record catches.
3. Run the composed pipelines; record catches.
4. Human review confirms every composition-only catch is a real failure (not an artifact of the pipeline's extra compute — control by giving individual checks matched sampling budgets).

## Verdict conditions (pre-registered)

- **CONFIRMED** iff the composed pipelines catch **≥ 5** human-confirmed failures across the battery that no individual check caught, under matched compute.
- **REFUTED** otherwise — the measurements are independently useful but composition adds no detection power, and the composition layer is not built.

## Cost and prerequisites

API credits; the measurement tooling; careful task construction (the adversarial design is most of the work).

## Exclusion criteria (pre-registered)

Excluded before running, counted and reported: tasks whose target failure is not confirmed by pre-run human adjudication. Any violation of the matched-compute control voids the affected comparison rather than being post-hoc corrected.

## Wanted from contributors

- Task construction with documented target failures (the matched-compute control is mandatory).
- Independent human adjudication of catches.
