# E3 pre-flight: the two flagged papers, checked

The protocol ([README](README.md) § Status and prior art) flagged two possibly-adjacent works to be
checked before any run. Both are now checked at abstract level — per the program's citation ceiling
(E0 PLAN § Guards), everything below is `abstract-checked`, not `verified`: no load-bearing claim may
rest on it until a named person reads the primary source. Checked 2026-07-14.

## Flag 1 — arXiv:2503.14749: does not preempt

"Uncertainty Distillation: Teaching Language Models to Express Semantic Confidence" (Hager, Mueller,
Duh, Andrews; v3 Dec 2025). Supervised fine-tuning that teaches a model to *verbalize* calibrated
semantic confidence — held-out data maps initial uncertainty estimates to probabilities, then SFT on
examples annotated with them. No hidden-state probe, no continuous regression target, no
probe-vs-verbalization comparison. It improves the very baseline E3 must beat, which makes it worth
citing in the baseline record — a stronger verbalized-confidence arm is conceivable via this method —
but it does not touch either claimed edge.

## Flag 2 — verbalized confidence vs sampling-based uncertainty: crowded, not identical

The suspected matched-compute comparison exists in several forms. None uses a trained hidden-state
probe as the competing predictor; all compare the verbal channel against *sampling-based* signals at
the output level:

- **arXiv:2505.23845** (Podolak & Verma) — the closest to the suspected paper: contrasts
  answer-then-confidence verbalization (overconfident) against semantic entropy (reliable but
  compute-heavy), with an explicit test-time-compute argument; forced long reasoning narrows the gap.
- **arXiv:2604.24070** — pre-registered negative result distilling self-consistency into verbal
  confidence on a 4B model; states the abstract-level finding that *internal representations carry
  substantially more correctness information than the verbal channel transmits* — thematically the
  nearest statement to H-VOL's premise, but via SFT distillation, not a probe, and its confirmatory
  arm failed.
- **arXiv:2502.06233** (CISC, Findings ACL 2025) and "Two Samples Are Enough" (OpenReview
  66D3rZrNjV; abstract snippet only, page bot-gated) — hybridization/weighting studies of verbal
  confidence with self-consistency, not head-to-head correctness-prediction benchmarks.

## Consequence for the E3 records

- **Edge (a) — continuous volume as a probe regression target — stands** as stated in the README.
  Secondary descriptions of Semantic Entropy Probes (arXiv:2406.15927) confirm its target is the
  binarized high/low class; the primary PDF resisted text extraction in this pass, so this
  confirmation itself is second-hand and flagged for primary-source verification.
- **Edge (b) narrows and must be stated narrowly**: not "first to compare verbalized confidence
  against a cheaper signal" (that space is active), but "first head-to-head of a *single-forward-pass
  hidden-state probe with a continuous volume target* against verbalized confidence." The baseline
  decision record cites 2505.23845, 2604.24070, and 2502.06233 as adjacent prior art and positions
  the claim against them explicitly.
- Both flags are dischargeable for design purposes; the run itself remains gated on primary-source
  verification of 2406.15927 (binarized-target confirmation) and 2503.14749 by a named reader, per
  the citation ceiling.

## Second round — full-text pass (2026-07-14)

The first round above is `abstract-checked`. A second-round review pass retrieved and read the **full text**
of the papers below (the SEP PDF that resisted extraction in round one, and four papers surfaced by the
audit). **The citation ceiling still binds:** everything here is `full-text-read-by-automation`, **not
`verified`** — no load-bearing claim rests on it until a named person reads the primary source, and the run
stays gated on those human reads (REGISTRATION-DRAFT § 9). The net effect of this pass was to **re-scope the
claim** (REGISTRATION-DRAFT § 1, § 7) and to **correct one false pre-mortem assertion**.

- **arXiv:2509.10625 — full text verified; preempts the naive probe-vs-verbalized-confidence framing.** A
  correctness probe (B4) beats verbalized confidence on Qwen2.5-7B, and correctness directions fail on math.
  Consequence: E3 cannot claim novelty for "a hidden-state signal beats verbalized confidence"; the surviving
  question is whether the **volume** target adds value over B4/B3/verbalized, which the redesigned added-value
  gates now require (e3-0005).
- **BbZKxrZCNn — Wayback-accessed full text; the closest prior art.** SEP authors (NeurIPS 2024 MINT
  workshop); trains a LASSO **regression** on **continuous semantic entropy** from hidden states — so
  "continuous uncertainty regression from a hidden state" is **not novel per se**. But it is in-distribution
  only, uses no volume, runs no OOD transfer, and no head-to-head against verbalized confidence or a
  correctness probe. E3's edge is defined strictly against it (volume target + cross-family transfer +
  B4/B3/verbalized head-to-head). The retrieved PDF is retained **outside** the repository (not committed); a
  named human read is required to move it onto the verified list.
- **arXiv:2503.14749 — version discrepancy resolved.** v1 is SFT-only (verbalization, no probe, no
  head-to-head); **v2/v3 add a P(IK) probe baseline vs verbalized confidence** (verbalized beat P(IK) in
  their tables). The E3 citation is version-anchored accordingly (stronger-conceivable-B1 at v1;
  adjacent probe-vs-verbalized prior art at v2/v3).
- **arXiv:2506.08572 — full text verified.** Correctness directions are near-orthogonal across tasks,
  isolated on math, and mixtures do not fix it. This is what makes the volume-transfer question sharp: a
  volume direction that *did* transfer would be doing something correctness directions provably do not.
- **arXiv:2606.02907 — full text verified; control adopted.** Its format-feature residualization protocol
  (regress family ID / length / option structure out of the hidden state, re-probe) is adopted as a
  registered control — the source of the e3-0005 length-residualized gate. Fidelity surviving residualization
  is stronger than leave-one-family-out alone.
- **arXiv:2606.02628 (NF4) — full text verified; corrects a pre-mortem false claim.** 4-bit (NF4) probing of
  Qwen2.5-7B works and is published; this **falsifies** PREMORTEM § 8's "no cited probe paper used a
  quantized host" and turns E3's 4-bit host from an unanswered objection into a scoped, precedented choice.

**Consequence.** The design flags of round one remain dischargeable; the claim is re-scoped and the prior-art
positioning is fixed (REGISTRATION-DRAFT § 1, § 7). The run remains gated on **named-reader** primary-source
verification of 2406.15927 (binarized target — now quoted verbatim in this pass), BbZKxrZCNn, 2503.14749,
and the four second-round papers; per-citation statuses live in `VERIFICATION.md`.
