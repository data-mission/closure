# 0008 — E8 instruction breakpoint: dose-response study of instructed revision, Phase 0 axis selection

- Status: proposed
- Deciders: closure research program contributors
- Scope: E8 (new, derived from E5's result)

## Context
E5's registered run refuted H-RELEASE, and in a stronger-than-registered form: instructed disregard (Arm B)
contaminated 1/107 downstream conclusions (0.9%) while mechanical contraction (Arm C) contaminated 11/107
(10.3%); B-vs-C cleared the Bonferroni-corrected threshold with **C worse** (p = 0.0089), A-vs-C did not
(p = 0.081), and C's completeness was non-inferior (0.992 vs 0.942). The task-level paired sign test agreed:
C worse on 9 tasks, B worse on 0 (p = 0.0039). A commissioned hostile audit rated the corpus competent,
correct, and honestly constructed but **shallow** — 1–2 reasoning operations per task, a naive baseline (Arm A)
that floors near zero on two of three task families, and `must_persist` items that are largely source echoes.

That result exposes a premise every remaining operator experiment silently rests on: that instructed revision
**fails somewhere**. In the E5 regime it did not. E4, any reformulated E5 line, and the later actuation hypotheses only have terrain
to stand on if there exists a difficulty regime where a plain instruction to retract and revise measurably
degrades. If no such regime exists at practical scale, the operators are solving a problem the model already
solves when asked, and closure-as-a-runtime-tool is unnecessary — a publishable negative, not a gap.

E8 measures that premise directly. It is a **dose-response study on the baseline itself, with no operators
anywhere**: scale task difficulty along pre-chosen axes and observe whether instructed revision (an E5 Arm-B
generation) degrades monotonically as difficulty rises. Because axes-chosen-after-seeing-results is the obvious
way to manufacture a break, the *choosing* is itself a registered research phase (Phase 0) that must freeze
before any probe is generated.

## Decision
- **Two program-level verdict conditions, pre-registered.** (a) Instructed revision breaks along at least one
  axis — contamination crosses the fixed threshold with a monotone dose-response across ≥ 3 dose levels. That
  terrain re-scopes the remaining operator experiments to it; it does **not** by itself confirm any operator
  hypothesis (the operator still has to beat instruction *in that regime*, which is a separate experiment).
  (b) No break along any frozen axis at practical scale — instructed revision holds everywhere tested. This is
  a program-level conclusion condition: closure-as-a-tool is unnecessary for revision, and the program records
  that as a negative result of record.
- **Phase 0 is a gating sub-registration.** E8 is NOT RUNNABLE until Phase 0 is frozen by public commit. Phase 0
  pre-registers, before any probe is generated:
  - **(i) Candidate axis set.** Enumerated and motivated, each from E5 evidence or the prior art already cited in
    `experiments/E5-reclosure/README.md`:
    - *context length / distractor volume* — the published contamination-under-instruction effects the E5 premise
      rested on grow with context size (arXiv:2506.08184, 2606.01435); E5 deliberately capped sources at ≤350
      tokens and scoped its verdict to that small-context regime (PROTOCOL.md §11 boundary 2), so this axis
      probes exactly the regime E5 excluded.
    - *number of accumulated corrections* — E5 injected a single ¬A; whether one clean retraction generalizes to
      many stacked retractions is untested and is where "pretend to forget" residue (arXiv:2410.00382) would
      accumulate.
    - *correction-chain interleaving (corrections of corrections)* — a later correction that overturns an earlier
      correction; the belief-revision-under-interference failures (arXiv:2406.19764, 2605.30219) are stated at
      single-revision depth.
    - *dependency depth between the corrected fact and the conclusion* — E5's audit found 1–2 reasoning ops per
      task; contamination that cascades through structurally similar errors (arXiv:2602.04288) predicts the break
      appears only past a reasoning-depth floor the E5 corpus never reached.
    - *distance / separation between the assumption and its correction* — anchoring resists explicit "ignore
      the anchor" instructions (arXiv:2412.06593); whether the residue scales with anchor-to-correction
      distance is untested in that literature — this axis measures it rather than assumes it.
    - *domain shift of the correction document* — a ¬A phrased in a different register/domain than A, testing
      whether retrieval-under-interference (arXiv:2506.08184) degrades when the correction does not lexically
      resemble what it corrects.
    - *summarization / compaction of the context* — replacing the accumulated context with an algorithmic
      summary between the correction and the question is a mechanical contraction applied to a live context,
      and E5's own registered result predicts the break directly: a single contraction application injected
      10.3% contamination against instruction's 0.9%, with the retained-conclusion-lost-support signature
      ([results record](../results/E5-reclosure/2026-07-15-registered-run/)); repeated summarize-and-continue
      cycles predict monotone accumulation of exactly that error class. Dose = number of compaction cycles
      (0/1/2/3) or compression ratio. Uniquely among the candidates, this axis avoids the instrument
      constraint below rather than colliding with it (compaction shortens sources). Classification note for
      Phase 0: this is a context-lifecycle property rather than a task property — Phase 0 decides whether it
      enters as an E8 axis or as a separately derived hypothesis.
  - **(ii) Selection criteria** for narrowing the candidate set to the final frozen axes: each retained axis must
    (1) have a dose parameter with ≥ 3 monotone levels that are operationally distinguishable, (2) hold the E5
    scoring instrument valid at every level (see the instrument constraint below), (3) be motivated by cited
    evidence that predicts a break, not by convenience, and (4) be independent enough of the others that a break
    on one is not mechanically a break on another. The narrowing decision and the dropped axes are recorded.
  - **(iii) The exact definition of "break."** A fixed contamination threshold (a single absolute rate, frozen in
    Phase 0, not chosen post-hoc) **plus** a monotone dose-response requirement: contamination must rise
    monotonically across ≥ 3 dose levels on that axis and cross the threshold at the top level. A single bump at
    one dose level is explicitly NOT a break.
  - **(iv) Anti-fishing guards.** Axes and dose levels frozen before any probe is generated; a capped probe budget
    per axis declared in Phase 0; multiplicity correction across the frozen axis count; every probe result
    reported (no axis and no dose level silently dropped after the fact — a dropped level voids that axis).
  - **(v) The known instrument constraint, named as Phase 0's first open problem (not solved here).** The frozen
    NLI scorer (0002, PROTOCOL.md §5a) runs `max_length=512`, truncation fails closed, and the E5 corpus capped
    sources at ≤350 tokens so pairs fit. Any long-context or high-distractor axis pushes sources past that bound
    and the scorer raises rather than scoring. That axis therefore needs either an instrument amendment (a new
    frozen scoring configuration, itself pre-registered) or a per-segment scoring design that keeps every scored
    pair under the token bound. Phase 0 must name this as its first open problem; it does not resolve it in this
    record.
- **Reuse, not rebuild.** E8 reuses the E5 harness, the frozen scoring instrument (0002), and the
  freeze-by-public-commit gate (0006). The dose-response arms are E5 Arm-B generations (instructed retract-and-
  revise, the frozen ARM-B-INSTRUCTION) run over probe tasks that vary one axis at a time. No Arm C, no
  contraction, no operator of any kind appears in E8.
- **Cost (estimate, API-only, no GPU).** Order-of-magnitude: roughly E5-scale per dose level per axis — a
  registered E5 arm was 60 tasks × 1 generation each at short context. With a small number of frozen axes
  and ≥ 3 levels each, total cost is a low single-digit multiple of one E5 run. This is an estimate, not a
  budget; the Phase-0 probe-budget cap sets the actual ceiling.

## Consequences
Gives the program a decision procedure for a question E5 turned from assumption into open: whether instructed
revision has a failure regime at all. Both outcomes are load-bearing — (a) tells the remaining operator
experiments where to aim and stops them from testing operators in a regime where instruction already wins; (b)
concludes the revision line with a negative that is publishable precisely because it contradicts a premise the
field has replicated. Making Phase 0 a frozen sub-registration before any probe exists is what keeps outcome (a)
from being manufactured: without frozen axes, a fixed threshold, and a monotone-across-≥3-levels break definition,
any dose-response study finds a break by choosing where to look after looking. The instrument constraint is
recorded as an open problem rather than papered over, because the most decision-relevant axes (context length,
distractor volume) are exactly the ones that break the current scorer.
