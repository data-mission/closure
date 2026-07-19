# E5 Arm-C re-examination — is the 10.3% contamination real echo or template artifact?

**Stakes:** E5's Arm-C contamination (11/107 = 10.28%) is the ONLY measured revision failure in the
entire program. E5's registered refutation rests on B (instructed) ≈ 0.9% vs C (mechanical contraction)
≈ 10.3% — the claim that the contraction operator injects contamination instructed revision does not.
If C's 10.3% is the same NLI template-collision artifact that collapsed E8-A3's "26%" to 0, that
separation reopens.

**Method:** the SAME claim-grounded discriminator that collapsed A3. For each of the 11 flagged Arm-C
items, read the stale `must_change[i]` conclusion + the `not_A_evidence` correction + every Arm-C claim
(mechanical contraction of Arm A). For the second-order F2 items, computed the corrected arithmetic
explicitly and checked whether the stale threshold verdict is TRUE or FALSE under the correction. Two
independent passes (a Sonnet forensic agent + my own cross-read of the load-bearing cases); arithmetic
verified.

## VERDICT: 0/11 REAL_ECHO. The 10.3% collapses to artifact. E5 B-vs-C separation reopens. ⚑

| # | task/item | stale must_change | corrected arithmetic | adjudication | decisive Arm-C evidence |
|---|---|---|---|---|---|
| 1 | F1-0004/0 | loop cannot complete on one fill | 400km range > 345km loop | FP_INTEGRATED | "updated 400 km range **exceeds** the 345 km loop"; 300km framed historical |
| 2 | F1-0004/1 | refuel stop / route split required | — | FP_INTEGRATED | no stop/split claim survives; only the loop-fits claim |
| 3 | F1-0007/0 | container exceeds certified weight | 21,000 < amended 22,000 kg | FP_INTEGRATED | "21,000 kg is **below** the amended 22,000 kg limit"; "exceeds original 20,000" historical |
| 4 | F1-0011/1 | ≥4 pallets must wait | 34 positions > 30 pallets | FP_INTEGRATED | "30 staged pallets **fit within** 34 positions" |
| 5 | F1-0012/1 | panel cannot start on time | 15 < 25-min window | FP_INTEGRATED | "fits within the 25-minute window, 10 min buffer" |
| 6 | F1-0016/1 | ≥3 tubes must be deferred | 36-tube rotor > 27 tubes | FP_INTEGRATED | "27 tubes **fit within** a single run" |
| 7 | F1-0022/1 | ~25 cars have no space | 400 capacity > 325 cars | FP_INTEGRATED | "400 cars **exceeds** the expected 325 cars" |
| 8 | **F2-0010/1** | Nwora's claim requires countersignature | $0.48×800=**$384** < $400 ⇒ stale FALSE | **DANGLING_RULE** | computes $384 (integrated); retains the *must_persist* rule "above $400 requires countersignature" UNAPPLIED; never asserts "Nwora requires" |
| 9 | **F2-0012/1** | Merrow lot requires broker filing | 4%×$50k=**$2,000** < $2,500 ⇒ stale FALSE | **DANGLING_RULE** | computes $2,000 (integrated); retains the *must_persist* rule "duty > $2,500 requires filing" UNAPPLIED; never asserts "Merrow requires" |
| 10 | F2-0013/1 | kitchen must prepare 7 trays | 280/60 → **5 trays** | FP_INTEGRATED | "rounds up to **5 trays**" — corrected value asserted, stale "7" gone |
| 11 | F2-0016/1 | silo holds 140t spare capacity | 3×90=**270t**, 270<350 ⇒ shortfall | FP_INTEGRATED | "270 tonnes is **below** the 350-tonne contract" — corrected shortfall, "140 spare" never appears |

**Counts: 0 REAL_ECHO · 9 FALSE_POSITIVE_INTEGRATED · 2 DANGLING_RULE.**

## What the two DANGLING_RULE items are (and are not)

They are NOT the model/contraction asserting the stale conclusion. Verified arithmetic:
- F2-0010: stale rate $0.55×800 = $440 > $400 (stale WAS true). Corrected $0.48×800 = **$384 < $400**
  → the stale "requires countersignature" is **FALSE under correction**. Arm C computed $384 and
  retained the general must_persist rule "a claim above $400 requires countersignature" verbatim, but
  never drew the entity-specific inference. The general rule does NOT entail the stale specific
  conclusion (because $384 < $400), so the NLI flag is a scaffold collision, same class as the other 9.
- F2-0012: stale 6%×$50k = $3,000 > $2,500 (stale WAS true). Corrected 4%×$50k = **$2,000 < $2,500**
  → stale "requires filing" is **FALSE under correction**. Same pattern.

The distinct thing they reveal is a **reasoning-completeness gap in mechanical contraction**:
`contract()` strips claims that contradict `not_A_evidence` but has no mechanism to force RE-APPLICATION
of a surviving must_persist threshold-rule to the newly-corrected computed value. So the corrected value
is present, the correct rule is present, but the final Boolean ("therefore Nwora does NOT require
countersignature") is never stated. This is an incompleteness of the contraction procedure, NOT the
model echoing a stale value, and NOT a measurement-instrument artifact per se — it is a genuine (if
minor) defect in Arm C's output completeness on second-order threshold tasks. It does not make the
stale conclusion asserted; it leaves the corrected conclusion un-stated.

## Consequence

- **E5's Arm-C 10.3% is not real contamination-by-echo.** 0/11 items assert the stale conclusion live;
  9/11 assert the CORRECTED outcome (integration), 2/11 leave the inference dangling without asserting
  either. The NLI instrument fired on the same historical/superseded-claim scaffold overlap that
  produced A3's phantom 26%.
- **Therefore E5's registered B-vs-C separation reopens** (⚑ owner). The registered refutation read C's
  10.3% as operator-injected contamination that instructed revision (B, 0.9%) avoids. Under the
  claim-grounded instrument, C's "contamination" is ~0 real — the contraction operator did NOT inject
  stale-conclusion contamination; it integrated the correction in 9/11 and left an incomplete-but-not-
  contaminated trace in 2/11. The B-vs-C contamination gap that the E5 verdict rests on is a measurement
  artifact of the same NLI instrument now known to fail on this template class.
- **This is the E5-C-ARTIFACT branch of the SYNTHESIS-GATE two-sided conclusion** (§4): "E5's B-vs-C
  separation requires re-adjudication → the program's flagship registered refutation reopens" — which
  the gate marks as warranting a public correction note (⚑ owner decision).
- **Distinct actionable (not a verdict-mover):** the DANGLING_RULE class is a real contraction-
  completeness defect worth a fix (force re-application of surviving must_persist rules to corrected
  values) — separate from the instrument question.

## Rigor / limitations
- Zero-spend, no model run. Pure read of banked Arm-C outputs + corpus + arithmetic.
- Two independent adjudication passes agreed on 9 FP; the 2 F2 dangling items were the only non-obvious
  cases and were resolved by explicit arithmetic (stale conclusion provably FALSE under correction) +
  confirming Arm C never states the stale entity-specific conclusion.
- The "0 real echo" is a statement about whether Arm C ASSERTS the stale conclusion — which is exactly
  what the E5 contamination metric measures. It does not claim the contraction is flawless (the 2
  dangling-rule items show it is not complete); it claims the contamination number is an instrument
  artifact.
- An NLI GPU re-probe (stale vs corrected hypothesis, per item) would machine-confirm the 9 collision
  cases and adjudicate whether the 2 dangling rule-sentences cross 0.7 by genuine entailment vs surface
  overlap — same probe pattern X1 emitted for A3. Not required to reach "0 real echo": no Arm-C output
  asserts the stale conclusion as its live answer.

## ADDENDUM — B-arm control (lead-requested): both arms collapse the same way

The team lead asked whether E5's Arm-B "contamination" (1/107 = 0.9%) is ALSO an artifact — because
if B collapses too, the whole B-vs-C separation is instrument noise on BOTH sides, not just C.

**Arm-B contaminated must_change items: exactly 1 — F1-0016 item1.** Adjudicated:
- STALE: "At least three tubes must be deferred to a later run."
- CORRECTION: swing-bucket rotor raised Spinix capacity to 36 tubes/run.
- Arm-B decisive claims: "the 24-tube capacity is superseded and no longer applies; the correct
  capacity is 36 tubes"; "all 27 tubes fit within the 36-tube capacity, no tubes need to be deferred
  or split." Conclusion: "no tubes need to be held back or rescheduled."
- ADJUDICATION: **FALSE_POSITIVE_INTEGRATED.** Arm B asserts the CORRECTED outcome explicitly and
  states the stale premise only as superseded. The NLI 0.7 flag is the same historical/superseded-
  scaffold collision as the 9 Arm-C FPs. (Note: F1-0016 item1 was also an Arm-C FP — the same item
  trips the instrument in both arms, which is itself evidence the flag tracks the sentence template,
  not the arm's behavior.)

**Per-arm E5 contamination, all re-adjudicated:**
| arm | flagged must_change | real echo | mechanism |
|---|---|---|---|
| A (naive append) | 3/107 = 2.8% | (not re-adjudicated in full, but same template family) | template collision expected |
| B (instructed) | 1/107 = 0.9% | **0** | 1 FP_INTEGRATED (F1-0016/1) |
| C (contraction) | 11/107 = 10.3% | **0** | 9 FP_INTEGRATED + 2 DANGLING_RULE |

**Strengthened conclusion.** The E5 B-vs-C gap (0.9% vs 10.3%) is NOT a real contamination difference:
both arms integrate the correction and assert the corrected outcome; the instrument fires on
template-collision, and the COUNT of collisions differs only because Arm C's mechanical contraction
retains MORE historical/superseded premises (it keeps the pre-correction claim as an explicit contrast
to a fixpoint, giving the max-over-premises NLI more shared-scaffold premises to clear 0.7 on). So C's
higher number is an artifact of contraction retaining more retracted-but-present claims — a property of
the CONTRACTION OUTPUT SHAPE, not of contamination. Under the claim-grounded instrument, all three arms
are ~0 real contamination. The registered B-vs-C separation is fully an instrument artifact.
