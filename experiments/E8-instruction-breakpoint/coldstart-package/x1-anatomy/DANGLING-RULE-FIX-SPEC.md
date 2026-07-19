# Contraction DANGLING_RULE fix — spec (not code)

## The defect (found in the E5 Arm-C re-exam, 2/11 items)
`contraction.contract()` iteratively removes claims that contradict `not_A_evidence` to a fixpoint. It
has NO mechanism to force RE-APPLICATION of a surviving conditional rule to a value that the correction
changed. Result: the corrected intermediate value is present, the correct threshold-rule is present, but
the final Boolean inference is never drawn — so the output neither asserts nor retracts the stale
conclusion; the stale requirement-sentence survives as an unapplied rule.

Two confirmed instances (arithmetic-verified in E5-ARMC-REEXAM.md):
- **F2-0010/1**: correction sets rate $0.55→$0.48; Arm C computes "$0.48 × 800 = $384" (corrected value
  present) and retains the must_persist rule "a claim above $400 requires the director's countersignature"
  (correct rule present) but never states "therefore Nwora's claim does NOT require countersignature".
  $384 < $400 → stale conclusion is FALSE under correction, but Arm C leaves it undrawn.
- **F2-0012/1**: correction sets duty 6%→4%; Arm C computes "$2,000" and retains "duty > $2,500 requires
  a formal broker filing" but never states "therefore Merrow does NOT require a filing". $2,000 < $2,500
  → stale conclusion FALSE, undrawn.

This is a COMPLETENESS gap in the contraction procedure, NOT contamination (the stale conclusion is not
asserted) and NOT a measurement-instrument artifact. It matters only for a future operator retest where
contraction is scored on completeness, not just non-contamination.

## Scope + what NOT to change
- This is the CONTRACTION operator (`contraction.contract()`), scored as Arm C. It is a FROZEN registered
  component — this spec is for a FUTURE operator-retest build, not a change to the banked E5/E8 runs. Do
  NOT touch the frozen path or re-score banked data with a changed contractor; that would break the
  registered comparison. This fix defines a v2 CONTRACTOR for the next campaign.
- Do NOT make the contractor a general reasoner. The fix is narrow: re-apply a SURVIVING conditional rule
  to a value the correction changed, when all the operands are present in the surviving claim set.

## The fix (mechanism)
After the contraction fixpoint, add a RULE-REAPPLICATION pass:
1. Identify surviving CONDITIONAL RULE claims — claims of the form "<quantity> <comparator> <threshold>
   ⇒ <consequence>" that survived contraction (they are must_persist rules; they never contradict
   not_A_evidence, so they always survive). Parse (quantity-anchor, comparator, threshold, consequence).
2. Identify the CORRECTED computed value for that quantity in the surviving claim set (the value produced
   AFTER the correction was applied — the claim that cites/derives from not_A_evidence).
3. If both are present and the rule is currently UNAPPLIED (no surviving claim states the consequence or
   its negation for THIS specific entity), EVALUATE the rule against the corrected value and EMIT the
   drawn conclusion as a new claim: "<corrected value> <comparator result> <threshold>, therefore
   <consequence holds / does not hold> for <entity>."
4. Fixpoint again (the newly-drawn conclusion could feed a further rule).

## Invariants / guards (must hold)
- SOUNDNESS: only emit a drawn conclusion when the corrected value and the rule's threshold are BOTH
  explicit in surviving claims and the comparator is unambiguous. If the corrected value is absent or the
  rule is ambiguous, leave it undrawn (do NOT guess) — under-drawing is safe; mis-drawing is not.
- MONOTONICITY: the reapplication pass may only ADD drawn-conclusion claims; it must never remove or
  alter a surviving claim (removal is contraction's job, already done).
- NO STALE REINTRODUCTION: the drawn conclusion must use the CORRECTED value; it must never restate the
  stale value as live. (This is what keeps the fix from becoming a contamination source.)
- ENTITY-SCOPING: the drawn conclusion must be scoped to the specific entity (Nwora / the Merrow lot),
  not the generic rule — the generic rule already survives; the gap is the entity-specific application.
- IDEMPOTENCE: running the pass twice yields the same output (a rule already applied for an entity is
  skipped in step 3).

## Acceptance test for the v2 contractor
- On F2-0010/1 and F2-0012/1: the v2 contractor emits "Nwora's claim does NOT require countersignature
  ($384 < $400)" and "Merrow does NOT require a filing ($2,000 < $2,500)" — the corrected, drawn
  conclusion. Under instrument-v2, these score 0 contamination (they assert the corrected outcome) AND 0
  dangling-rule (the inference is complete).
- On the 9 FP_INTEGRATED items: no change (they already drew the corrected conclusion).
- REGRESSION: on a synthetic case where the corrected value is ABSENT, the pass leaves the rule undrawn
  (soundness guard) — never fabricates a value to apply the rule to.
- CONTAMINATION GUARD: on a synthetic case where applying the rule would require the STALE value, the pass
  declines (no stale reintroduction).

## Note on stakes
This does not change any E5/E8 verdict. It is a defect-of-record + a build spec for the eventual operator
retest, where a corrected contraction operator must be COMPLETE (draws the final Boolean) as well as
non-contaminating. The E5-C-ARTIFACT verdict stands independently: 0/11 real echo regardless of this fix.
