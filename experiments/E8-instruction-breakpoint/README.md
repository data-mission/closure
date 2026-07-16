# E8 — Instruction breakpoint: does instructed revision fail anywhere?

**Question:** Is there a task-difficulty regime in which **instructing a model to retract an assumption and revise everything that depended on it** measurably degrades — and if so, along which axes and at what dose? E8 is a dose-response study on the instruction baseline alone. It contains **no operators**: no mechanical contraction, no enforcement, no runtime mechanism of any kind.

**Hypothesis:** [H-BREAKPOINT](../../HYPOTHESES.md#h-breakpoint--instructed-revision-degrades-along-measurable-difficulty-axes) — instructed revision degrades along measurable difficulty axes; there exists a regime where a plain retract-and-revise instruction fails. Its kill condition is E8 outcome (b): no break along any frozen axis at practical scale.

## Status

`DERIVED` — created after E5's result, registered before design freeze. Phase 0 (axis selection) is a gating sub-registration; E8 is NOT RUNNABLE until Phase 0 is frozen by public commit ([0008](../../decisions/0008-e8-instruction-breakpoint.md), [0006](../../decisions/0006-reproducibility-and-freeze.md)).

## Why this experiment exists

E5 tested whether mechanical contraction beats instructed disregard on downstream contamination. Its registered run refuted that: instructed disregard (Arm B) contaminated 1/107 must-change conclusions (0.9%), mechanical contraction (Arm C) contaminated 11/107 (10.3%), B-vs-C cleared the Bonferroni-corrected threshold with **C worse** (p = 0.0089), and C's completeness was non-inferior (0.992 vs 0.942). The task-level paired sign test agreed (C worse on 9 tasks, B worse on 0; p = 0.0039). A commissioned hostile audit rated the corpus competent, correct, and honestly constructed but **shallow** — 1–2 reasoning operations per task, a naive baseline flooring near zero on two of three task families, `must_persist` items largely source echoes.

Every remaining operator experiment silently assumes instructed revision fails *somewhere*. In the E5 regime it did not. E8 measures that premise directly instead of assuming it: scale difficulty until the instruction baseline degrades, or establish that it does not at practical scale.

## Prior art (axes motivated from it)

E8's candidate axes are drawn from the same literature E5 rested on ([E5 README](../E5-reclosure/README.md), [VERIFICATION.md](../../VERIFICATION.md)):

- Contamination-under-instruction grows with **context size** (arXiv:2506.08184, 2606.01435) — E5 capped sources at ≤350 tokens and scoped its verdict to that regime, so context length / distractor volume probe exactly what E5 excluded.
- Errors in context bias later generations toward structurally similar errors, 10–20% drops (arXiv:2602.04288) — predicts a break only past a **dependency-depth** floor the shallow E5 corpus never reached.
- "Models pretend to forget": the final layer emits forgotten while earlier layers still compute from the content (arXiv:2410.00382) — residue that would accumulate under **many stacked corrections**.
- Belief-revision-under-interference failures are stated at single-revision depth (arXiv:2406.19764, 2605.30219) — **correction-of-correction interleaving** is untested.
- Anchoring resists explicit "ignore the anchor" instructions (arXiv:2412.06593); whether the residue scales with **assumption-to-correction separation** is untested in that literature — this axis measures it.
- E5's own registered result: one mechanical contraction of a live context injected 10.3% contamination vs 0.9% instructed, with a retained-conclusion-lost-support signature ([results record](../../results/E5-reclosure/2026-07-15-registered-run/)) — predicts **summarization/compaction cycles** accumulate exactly that error class; the one candidate axis that avoids the instrument constraint below rather than colliding with it.

The full candidate set, motivations, and the narrowing criteria are registered in [0008](../../decisions/0008-e8-instruction-breakpoint.md); they are frozen in Phase 0, not here.

## Protocol sketch

1. **Phase 0 — axis selection (registered, freezes before any probe).** Pre-register the candidate axis set (i), the selection criteria that narrow it (ii), the exact break definition (iii), the anti-fishing guards (iv), and the instrument constraint as the first open problem (v). All five are specified in [0008](../../decisions/0008-e8-instruction-breakpoint.md). Nothing downstream runs until Phase 0 is frozen by public commit.
2. **Freeze.** The frozen axes, dose levels, break threshold, per-axis probe budget, and any instrument amendment are committed (0006 freeze-by-public-commit; OSF registration is the act that counts, the git commit is necessary-not-sufficient).
3. **Dose-response arms.** For each frozen axis, generate probe tasks that vary that one axis across ≥ 3 dose levels, holding the others fixed. Each probe is run through an **E5 Arm-B generation** (the frozen retract-and-revise instruction, [ARM-B-INSTRUCTION](../E5-reclosure/ARM-B-INSTRUCTION.md)) and scored for contamination with the frozen E5 instrument ([0002](../../decisions/0002-grounding-measurement.md), PROTOCOL §5a) — subject to the instrument constraint below.
4. **Read the dose-response curve** against the pre-registered break definition, per axis, with multiplicity correction across the frozen axis count.

Reuses the E5 harness, the E5 scoring instrument, and the E5 freeze gate throughout. Builds no new operator.

## Instrument constraint (Phase 0's first open problem)

The frozen NLI scorer runs `max_length=512` and **fails closed** on truncation; the E5 corpus capped sources at ≤350 tokens so pairs fit ([0002](../../decisions/0002-grounding-measurement.md), PROTOCOL §5a). The context-length and distractor-volume axes push sources past that bound, at which point the scorer raises rather than scoring. Those axes therefore require either a pre-registered instrument amendment (a new frozen scoring configuration) or a per-segment scoring design keeping every scored pair under the token bound. Phase 0 names this as its first open problem; [0008](../../decisions/0008-e8-instruction-breakpoint.md) does not solve it.

## Verdict conditions (pre-registered)

Two program-level outcomes, both load-bearing:

- **(a) BREAK FOUND** — along at least one frozen axis, contamination rises monotonically across ≥ 3 dose levels **and** crosses the frozen absolute threshold at the top level, surviving multiplicity correction. Consequence: that regime re-scopes the remaining operator experiments (E4, E5-line, later actuation hypotheses) to the difficulty regime where instruction demonstrably degrades. **A break does NOT confirm any operator hypothesis** — the operator must still beat instruction *in that regime*, which is a separate experiment. (a) opens terrain; it does not settle it.
- **(b) NO BREAK — kill condition for H-BREAKPOINT.** No frozen axis produces a monotone-across-≥3-levels crossing of the threshold at practical scale. Consequence: instructed revision holds everywhere tested, closure-as-a-runtime-tool is unnecessary for revision, and the program records a negative result of record. Publishable precisely because it contradicts a premise the field has replicated ≥ 7 times.

A single-dose bump that does not extend to a monotone curve is **not** a break (0008 (iii)). No axis or dose level may be dropped after results are seen; a dropped level voids that axis (0008 (iv)).

## What this experiment does NOT test

- **No operators, anywhere.** E8 has no Arm C, no mechanical contraction, no enforcement, no runtime mechanism. It measures the instruction baseline alone. Whether any operator beats instruction in a found break regime is out of scope and belongs to a re-scoped E4/E5-line experiment.
- **Not a re-run of E5.** E5 compared arms at one difficulty; E8 varies difficulty on one baseline. E8 does not re-open E5's B-vs-C verdict.
- **Not a long-context capability claim.** Where the instrument constraint forces per-segment scoring or an amendment, the verdict is scoped to what that scoring configuration can validly measure — not to long-context revision in general.
- **Break ≠ operator justification.** Outcome (a) re-scopes the operator experiments; it does not confirm them. Outcome (b) concludes the revision line; it does not touch the measurement hypotheses (E0–E3) or lowering/composition (E6, E7), which do not depend on instructed revision failing.
