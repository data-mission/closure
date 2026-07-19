# Changelog — vs the archived v1 record (DOI 10.5281/zenodo.21399411)

**What changed:**

The archived v1 snapshot (tag `e5-verdict-2026-07-16`) reported E5's registered verdict as REFUTED:
mechanical contraction (Arm C) showed significantly higher downstream contamination than instructed
disregard (Arm B) — 10.3% vs 0.9%, Bonferroni-corrected p = 0.0089 — and that separation was read as
refuting H-RELEASE (the hypothesis that mechanical context rebuild is a safe substitute for instructed
revision).

This version adds one document, `E5-CORRECTION.md`, that withdraws that reading. A post-verdict
adversarial audit found the B-vs-C separation is an artifact of the contamination-scoring instrument
(bidirectional NLI entailment), not a real behavioral difference between the two arms: under a
claim-grounded replacement instrument, all three arms score approximately zero real contamination, and
a single flagged sentence template triggers identically regardless of which arm produced it.

**Why it changed:**

The program's own falsification discipline was turned on its own registered result. The same instrument
was independently found to be producing template-collision false positives on a different corpus inside
the same research program (the E8 instruction-breakpoint campaign's A3 axis), which prompted a
re-examination of E5 using the same corrected instrument. The re-examination is disclosed in full,
including a separate, real, non-contamination defect (DANGLING_RULE) found in the same review.

**What did NOT change:**

- The original registered run artifacts, raw generations, and scores — unchanged. This is a
  re-interpretation of the same banked data under a corrected instrument, not a re-run, and not a
  correction of data or protocol execution.
- The E8 program's own independent verdict (Block B, no axis broke) — unaffected by this correction.
- Any claim outside the specific B-vs-C contamination-separation reading.

**Net effect on the program's claim register:** H-RELEASE moves from `REFUTED` back to `REOPENED`. The
program currently has no valid measurement of an operator-induced revision failure in this line.
