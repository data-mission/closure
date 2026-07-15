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
