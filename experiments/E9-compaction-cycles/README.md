# E9 — Compaction cycles: does an iterated summarizer accumulate revision error?

**Question:** When a live reasoning context is repeatedly **compacted** (summarize-and-continue) between
correction turns, does the model **lose corrections it would otherwise apply** — does an iterated
summarizer operator accumulate revision contamination that a plain no-compaction instruction, over the
same turns, does not?

**Hypothesis:** **H-COMPACT** (a Mission X exploratory hypothesis, not a registered entry in
[HYPOTHESES.md](../../HYPOTHESES.md); it descends from the operator-line question left open by
[H-BREAKPOINT](../../HYPOTHESES.md#h-breakpoint--instructed-revision-degrades-along-measurable-difficulty-axes)
and [H-RELEASE](../../HYPOTHESES.md#h-release--revision-is-an-operation-not-a-request)) — an iterated
summarize-and-continue operator applied to a live reasoning context accumulates revision contamination
across cycles, exceeding the no-compaction instruction baseline and rising monotonically with cycle
count. E9 is the separately-staged study E8
Phase 0 promised when it dropped compaction from the E8 axis set: a summarize-and-continue cycle is a
*mechanical contraction applied to a live context* — an **operator** — so E8 (registered operator-free)
excluded it, and the mechanism gets its own experiment rather than being mislabelled as task difficulty.

## Status and grade

`RUN — EXPLORATORY (not pre-registered)`. E9 was built and executed as part of the Mission X adversarial
campaign, not filed as a registered experiment beforehand. It is declared exploratory: its instrument,
corpus, and pins are frozen and disclosed, but there is no OSF-style pre-registration timestamp, and the
verdict is reported at exploratory grade. The design (`../E8-instruction-breakpoint/coldstart-package/x5-e9/DESIGN.md`)
was authored before the run; the deviations that occurred at execution (10-shard parallel generation, a
device-ported scorer) are disclosed in [PROTOCOL.md §Deviations](PROTOCOL.md).

## Why the operator framing is load-bearing

- **The summarizer is the operator.** A compaction cycle reads the live working context and REPLACES it
  with a model-generated summary, then generation continues from the summary. That is the shape of the E5
  Arm-C contraction operator, except the reduction function is a model summarizer instead of the
  deterministic claim-pruner. E9 is therefore **operator-bearing** — it must be framed as its own
  hypothesis, never as a difficulty axis.
- **The contrast is operator-vs-instruction over MATCHED turns.** Both arms do the identical multi-turn
  task with identical corrections in identical order and the identical final retract-and-revise
  instruction; they differ ONLY in whether the context is compacted between turns. Any contamination
  delta is attributable to the compaction operator alone — not to turn count, correction count, or
  context growth.

## Protocol

1. **Corpus.** 150 fresh F3-family scenarios, each a numeric multi-step task seeded with values that are
   later corrected. Every scored `must_change` item is a bare computed value of the form
   `"The <label> is <value>."` — numeric-only, single-proposition, no threshold clause and no verdict word
   (the grammar the frozen NLI scores correctly and that dodges the compound-string artifact class found
   in X1). A construction-time polarity guard asserts every `must_change` holds the STALE-world value and
   differs from the correct-final value (the A1-inversion guard, fail-closed).
2. **Dose = number of compaction cycles `k ∈ {1, 2, 3}`.** Each scenario is instantiated at every `k` in
   both arms, so a matched family appears 6 times (3 doses × 2 arms).
3. **Arm N — no-compaction instruction baseline.** The `k` corrections are delivered one per turn; the
   FULL transcript is retained at every turn; the frozen E5 Arm-B retract-and-revise instruction is
   appended at the final answer turn. Isolates "the model saw everything and was told to revise."
4. **Arm S — summarizer / compaction operator.** Identical turn sequence and corrections, but BEFORE each
   correction turn the live context is REPLACED by a model-generated summary (frozen model, pinned
   summarizer instruction, 30–50% compression band). Generation continues from `[summary] + [new
   correction]`; the same retract-and-revise instruction is appended at the final turn. Isolates "the
   model revised through `k` compaction boundaries."
5. **Dual scoring + comparability gate.** Every final answer is scored by BOTH the frozen NLI instrument
   (carried forward bit-for-bit from E5/E8 for direct comparability) AND instrument-v2 (the claim-grounded
   value-echo test). The registered contamination number is instrument-v2's; the NLI number is reported
   alongside. Because strings are numeric-only, the two must agree on ≥ 98% of items; a disagreement rate
   > 2% VOIDS the numeric-only construction and halts before verdict. Contamination = fraction of
   `must_change` (stale value) items the final answer still asserts as live; completeness = fraction of
   `must_persist` items retained.

## Verdict conditions (pre-stated, two-sided)

- **CONFIRM (a):** compaction contamination rises monotonically across ≥3 cycle levels, crosses the frozen
  θ=5% threshold at the top level, AND beats the matched no-compaction baseline (paired McNemar). This
  would be the first demonstrated regime where a real operator measurably degrades revision that a plain
  instruction handles — it re-opens the operator line with a concrete failing operator.
- **KILL (b):** compaction contamination does NOT rise monotonically across the cycle levels AND does NOT
  cross θ at the top level. E5's single-shot contraction result does not scale into an iterated-operator
  failure regime; the compaction line closes with a bounded negative.

## Verdict (exploratory) — **H-COMPACT HOLDS CLEAN: corrections survive compaction**

Kill condition (b) fired. Corrections SURVIVE compaction cycles; the operator does NOT accumulate revision
error at this operating point.

- **instrument-v2 contamination = 0 / 1800 real at every (arm, dose):** N-arm 0/150, 0/300, 0/450; S-arm
  0/150, 0/300, 0/450. No real correction loss under compaction on either arm.
- **The frozen NLI showed the trap.** The OLD instrument produced a RISING S-arm curve 0 / 9 / 18 — the
  exact monotone shape that would have FALSELY confirmed H-COMPACT under the pre-audit instrument. The
  screen adjudicated all 27 flags against all 900 stale-total pairs and found **0/27 real, all
  supersession-scaffold artifact** — the same template-collision class as A3 and E5 Arm-C. E9 is its fifth
  independent confirmation. (Screen detail: [E9-SCREEN-APPENDIX.md](../E8-instruction-breakpoint/coldstart-package/mission-x/E9-SCREEN-APPENDIX.md).)
- **Comparability gate: 33/1800 = 1.83% ≤ 2% → PASS** (the two instruments are comparably scored).

## Scope limits (do not over-read)

One model (`claude-sonnet-5`), one pinned compression band (30–50%), one summarizer instruction (sha
`305f7e27`). E9 measures compaction AT that operating point; it does not generalize to other models,
bands, or summarizers. The dose-response secondary read is honestly bounded (a shallow curve at floor is
underpowered) — the load-bearing verdict is the flat, at-floor contamination, not a powered slope.

## Novelty / related work

NON-DUPLICATE on three structural axes vs the compaction literature (full differentiation in
`../E8-instruction-breakpoint/coldstart-package/x5-e9/X5-NOTES.md`): (i) the DV is instructed-revision
fidelity (contamination / persistence), NOT end-task accuracy, constraint erasure, or KL drift; (ii) an
operator-vs-no-compaction **matched-turn baseline** on a revision task, which the cited work lacks; (iii)
the tie to E5's registered contraction result. E9 does NOT claim primacy on iterating compaction
(arXiv:2607.08032 iterates it for end-task error) — its claim is a matched baseline on a
correction-fidelity DV.

## Pointers

- Design + apparatus: `../E8-instruction-breakpoint/coldstart-package/x5-e9/` (`DESIGN.md`, `X5-NOTES.md`,
  `driver/run_e9.py`, `driver/build_e9_corpus.py`, `driver/SUMMARIZER-INSTRUCTION.md`, `corpus-schema/`).
- Verdict in program context: `../E8-instruction-breakpoint/coldstart-package/mission-x/MISSION-X-VERDICT.md` §2.7.
- S-arm screen: `../E8-instruction-breakpoint/coldstart-package/mission-x/E9-SCREEN-APPENDIX.md`.
- On-Mini run data: `~/e9-driver/` (driver + derived MPS scorer) and the E9 run bank on the Mini
  (10-shard gen logs, dual-scored results, `_oracle`/comparability outputs).
