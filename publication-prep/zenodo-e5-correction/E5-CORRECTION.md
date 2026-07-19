# Correction note — E5 reclosure: the Arm-B-vs-Arm-C separation is a measurement artifact

**Status: DRAFT for owner review. Publication is the owner's act, not this document's.**

**Affects:** E5 (three-arm reclosure comparison, registered run 2026-07-15). **Correction class:**
measurement-instrument artifact invalidating a registered comparison; no data fabrication, no protocol
violation — a scoring-instrument limitation that the registered analysis did not detect and that the
program's own subsequent audit did.

## Summary of the correction

The registered E5 result reported a contamination separation between Arm B (instructed revision, 0.9%)
and Arm C (mechanical contraction, 10.3%), and read that separation as evidence that the contraction
operator injects contamination which instructed revision avoids — refuting the release-time hypothesis
(H-RELEASE) that a contraction operator is a safe substitute for instructed revision.

A subsequent audit of the scoring instrument (below) finds that this separation **does not exist under
a valid contamination test**. The contamination metric — a bidirectional NLI entailment check
(DeBERTa-v3-large-MNLI, threshold 0.7, max over premises) between a model output and the stale
`must_change` sentence — fires on the SHARED requirement scaffold between the stale and the corrected
sentences, not on any assertion of the stale conclusion. Under a claim-grounded value/verdict test that
scores whether the output actually asserts the stale value/verdict (excluding the shared threshold
constant, retraction clauses, unit collisions, and label ordinals), **all three E5 arms carry ~0 real
contamination.** Arm C's higher raw count reflects a property of the contraction OUTPUT SHAPE, not
contamination (it retains superseded premises as explicit contrasts, giving the max-over-premises NLI
more shared-scaffold premises to clear 0.7).

**Consequence: E5's registered refutation of H-RELEASE is withdrawn. H-RELEASE returns to REOPENED
(from REFUTED).** The program has no valid measurement of an operator-induced revision failure; the
only such measurement it had was this artifact.

## How the audit found it (the program auditing itself, before external discovery)

The E8 instruction-breakpoint campaign's post-verdict adversarial audit found the SAME NLI instrument
producing a phantom "26% contamination floor" on the E8-A3 corpus that collapsed to 0 real under
hand-adjudication + a claim-grounded discriminator (200 flagged items → 0 real, cross-validated by two
blind auditors + hand checks). Because A3 and E5 share the instrument and a near-identical stale/
corrected requirement-sentence template, the audit re-examined E5 Arm C with the same discriminator.
This correction is a result of the program's own falsification discipline applied to its own registered
result — surfaced by internal audit, not by an external reviewer.

## Evidence — all 11 Arm-C flagged items (contraction), re-adjudicated

The 11 flagged items are the entirety of Arm C's must_change contamination (11/107 = 10.28%). Each was
re-read against the stale conclusion, the correction, and every Arm-C claim; the second-order (F2)
items' arithmetic was computed explicitly.

| task/item | stale conclusion | corrected arithmetic | adjudication | decisive Arm-C claim |
|---|---|---|---|---|
| F1-0004/0 | loop cannot complete on one fill | 400km range > 345km loop | integrated (FP) | "updated 400 km range exceeds the 345 km loop" |
| F1-0004/1 | refuel stop / route split required | — | integrated (FP) | no stop/split claim survives; loop-fits asserted |
| F1-0007/0 | container exceeds certified weight | 21,000 < amended 22,000 kg | integrated (FP) | "21,000 kg is below the amended 22,000 kg limit" |
| F1-0011/1 | ≥4 pallets must wait | 34 positions > 30 pallets | integrated (FP) | "30 pallets fit within 34 positions" |
| F1-0012/1 | panel cannot start on time | 15 < 25-min window | integrated (FP) | "fits within the 25-minute window" |
| F1-0016/1 | ≥3 tubes must be deferred | 36-tube rotor > 27 tubes | integrated (FP) | "27 tubes fit within a single run" |
| F1-0022/1 | ~25 cars have no space | 400 capacity > 325 cars | integrated (FP) | "400 cars exceeds the expected 325 cars" |
| F2-0010/1 | claim requires countersignature | $0.48×800 = $384 < $400 ⇒ stale FALSE | **dangling rule** | computes $384; retains rule "above $400 requires…"; never applies it |
| F2-0012/1 | lot requires broker filing | 4%×$50k = $2,000 < $2,500 ⇒ stale FALSE | **dangling rule** | computes $2,000; retains rule "duty > $2,500 requires…"; never applies it |
| F2-0013/1 | must prepare 7 trays | 280/60 → 5 trays | integrated (FP) | "rounds up to 5 trays" |
| F2-0016/1 | silo holds 140t spare | 3×90 = 270t, 270 < 350 ⇒ shortfall | integrated (FP) | "270 tonnes is below the 350-tonne contract" |

**Count: 0 real echo · 9 corrected-and-integrated (instrument false positive) · 2 dangling-rule.**
Zero of the 11 Arm-C outputs assert the stale conclusion as their live answer.

## The airtight closer: the same item flags in BOTH arms

Arm B (instructed revision) had exactly one flagged item, F1-0016 item1. It is the SAME item that flags
in Arm C, and it is equally a false positive: Arm B asserts "the 24-tube capacity is superseded … the
correct capacity is 36 tubes … all 27 tubes fit … no tubes need to be deferred." A single sentence
template tripping the instrument in BOTH arms is direct evidence that the flag tracks the sentence
SHAPE, not the arm's behavior. The registered 0.9%-vs-10.3% gap is a difference in how many
template-collisions each arm's phrasing happens to produce, not a difference in contamination.

## Honest disclosure: a real (separate) defect the audit also found — DANGLING RULE

Two of the 11 Arm-C items (F2-0010, F2-0012) are NOT contamination but ARE a genuine defect in the
mechanical contraction procedure, disclosed here in full. In both, contraction correctly recomputes the
corrected intermediate value ($384; $2,000) and correctly retains the governing threshold-rule, but
never draws the final entity-specific Boolean ("therefore this claim does NOT require a
countersignature / filing"). Arithmetic confirms the stale conclusion is FALSE under the correction
($384 < $400; $2,000 < $2,500), so this is under-completion, not stale-echo — the output asserts
neither the stale nor (explicitly) the corrected conclusion. This is a completeness gap in the
contraction operator (it lacks a mechanism to re-apply a surviving rule to a correction-changed value),
independent of the measurement-instrument question, and it does not change the "0 real echo" verdict. A
fix is specified separately (rule re-application pass, with soundness/no-stale-reintroduction guards)
and is gated to any FUTURE operator retest — it does not touch the frozen registered contraction path.

## The replacement instrument (certification summary)

The re-adjudication uses a claim-grounded revision-fidelity test (instrument-v2) that scores whether an
output asserts the stale computed value and/or stale verdict direction as live, excluding: the shared
threshold constant, the correct-final value, supersession/retraction clauses, unit collisions (e.g.
"120 tonnes" vs "120 hectares"), and label ordinals (e.g. "Silo 4"). Certification:
- 200 E8-A3 NLI-flagged items → 0 real; full A3 sweep (786 must_change items; canonical verdict basis
  756 post-pruning) → 0 real.
- Positive controls (it MUST be able to fire): 10/10 synthetic stale-echo injections detected;
  adversarial hardening 60/60 bare-stale-sentence, 40/40 subtle F2 echo, 30/30 verdict channel; negative
  control (corrected value injected) 0/60 false fires.
- Two independent adjudication passes on the E5 items agreed (9 FP + 2 dangling-rule); arithmetic
  verified; cross-checked against a second prototype (784/786 agreement; the 2 differences were the
  unit-collision false positives the second prototype lacked a unit guard for).
- Positioning vs prior art: the test shares Proof-Carrying Numbers' (arXiv:2509.06902) numeric-span
  verification substrate and adopts its policy vocabulary (exact/alias/tolerance/qualifier), but scores
  revision fidelity against a stale↔corrected PAIR (directional echo) rather than faithfulness of a span
  to a single structured source value — a task PCN does not model.

## Scope of the correction (what does and does not change)

- CHANGES: E5's B-vs-C contamination separation is withdrawn as an instrument artifact; H-RELEASE
  returns to REOPENED; the claim "contraction injects contamination that instructed revision avoids" is
  not supported by E5.
- DOES NOT CHANGE: E5's other registered outputs that do not rest on the B-vs-C contamination gap; the
  E8 program verdict (Block B, no axis broke) which is independent of E5; the frozen registered run
  artifacts (unchanged — this is a re-interpretation of the same banked data, not a re-run).
- BROADER FINDING (disclosed): the modal failure across the whole revision line was the MEASURING
  INSTRUMENT, not the model — the NLI contamination metric produces template-collision false positives
  on near-identical stale/corrected requirement sentences. Every measured "revision failure" in the
  program (A3 floor, E5 Arm C) has re-adjudicated to instrument artifact; no model revision failure
  remains measured on any validly-instrumented corpus.

---
*Draft prepared from the internal audit record (E5-ARMC-REEXAM.md, instrument-v2 certification, the
SYNTHESIS-GATE adjudication). Numbers and quotes are from the banked 2026-07-15 E5 artifacts and the
frozen corpus. For owner review; owner decides publication venue, wording of the public status change,
and whether the dangling-rule defect is disclosed in the same note or separately.*
