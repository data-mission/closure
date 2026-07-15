# e3-0003 — Baselines: the comparator set and the comparison procedure

- Status: proposed
- Deciders: closure research program contributors
- Scope: E3

This record is e3-scoped pending a merge-time renumbering into the global `decisions/` sequence (see
`README.md` in this directory).

## Context

The E3 protocol (`../README.md` § Protocol step 3, § Evaluation (b)) names four comparators — "SEP-style binarized
probe; correctness probes (P(IK)-style); the model's verbalized confidence; naive predictive entropy" — and the
downstream evaluation "correctness prediction vs all baselines." It does not fix how each baseline is elicited or
parsed, over which items they are compared, or the statistical procedure of the comparison. Verbalized confidence
is the load-bearing baseline: the protocol's CONFIRMED condition requires the probe to **beat verbalized
confidence** on correctness prediction, so an under-specified or deliberately weak verbalized-confidence arm would
make a probe win worthless. Each comparator and the comparison procedure are fixed here. The verdict conditions
themselves are not restated — they live in `../README.md` § Verdict conditions; this record fixes the procedure that
feeds them.

## Decision

- **B1 — verbalized confidence (the arm H-VOL must beat).** Elicited in a clean two-turn exchange: the model first
  answers the task prompt, then in a second turn is asked for its confidence. The elicitation utterance is frozen
  **verbatim** in this record so it cannot drift between runs:

  > On a scale from 0 to 100, what is the probability that your answer above is correct? Reply with a single
  > integer between 0 and 100 and nothing else.

  The confidence utterance is decoded **greedy / argmax** (deterministic), so the confidence number does not itself
  add sampling variance to the comparison; if a greedy path is unavailable for any reason it is recorded, not
  silently replaced. **Parse rule:** the first integer in `[0, 100]` appearing in the reply. On a parse failure the
  item gets **one identical retry** (same prompt, same greedy decode); if it still fails to parse it is marked
  **missing** and the missing count is reported. B1 is intentionally the strongest simple verbalized arm the
  protocol allows, so that beating it is a real result.

- **B2 — SEP-style binarized probe.** A logistic probe trained to predict the **median-split** (high/low) class of
  the e3-0002 volume from the same pre-sampling hidden state e3-0001 uses. This is the binarized target Semantic
  Entropy Probes (arXiv:2406.15927) already demonstrated; it is included precisely so E3 must show **more** than it
  — the protocol's REFUTED branch fires if the signal "exists only at binary granularity (already known from SEP)."
  Sharing e3-0001's input vector and standardizer (train-split fit) keeps B2 a fair binarized counterpart of the
  continuous probe rather than a differently-fed model.

- **B3 — naive predictive entropy.** The Shannon entropy of the next-token distribution at the last prompt token,
  computed from the **same forward pass** that produces the probe input vector (e3-0001). No sampling, no extra
  forward passes — zero additional cost. It is the cheapest possible uncertainty signal and the floor the probe and
  the SEP-style baseline are expected to clear.

- **B4 — P(IK)-style correctness probe.** A linear probe trained **directly on correctness labels** (whether the
  model's answer is correct) from the same pre-sampling hidden state, rather than on the volume target. It measures
  how much correctness is linearly readable from the state without the volume detour, isolating whether E3's
  volume-target framing buys anything over probing correctness directly.

- **Comparison procedure.** Every comparator and the E3 probe are scored as **correctness predictors** by AUROC
  over the **answerable subset** (items with a defined correctness label), so the metric is identical across arms
  and independent of each arm's native output scale. Pairwise differences (probe vs each baseline, B1 first) are
  reported with **paired bootstrap confidence intervals** over prompts, so the comparison accounts for shared item
  difficulty. The procedure — AUROC, answerable subset, paired bootstrap, the resample count and CI level — is
  **pre-registered** in the frozen config (e3-0004) before any real correctness label is scored.

- **Prior art and the exact claimed edge.** Adjacent work, from `../PREFLIGHT.md`: arXiv:2503.14749 (uncertainty
  distillation — SFT that teaches a model to *verbalize* calibrated semantic confidence) **does not preempt** E3,
  but is cited because it could furnish a **stronger B1** — a fine-tuned verbalized-confidence arm — and a reviewer
  should know the verbalized baseline has a stronger conceivable form. arXiv:2505.23845 (answer-then-confidence
  verbalization vs semantic entropy, with a test-time-compute argument), arXiv:2604.24070 (internal representations
  carry more correctness information than the verbal channel transmits — via SFT distillation, confirmatory arm
  failed), and arXiv:2502.06233 (CISC, verbal-confidence/self-consistency hybridization) are cited as the crowded
  verbal-vs-sampling space E3 sits beside. Per `../PREFLIGHT.md`, the claimed edge is stated **narrowly**: not
  "first to compare verbalized confidence against a cheaper signal" (that space is active), but the **first
  head-to-head of a single-forward-pass hidden-state probe with a continuous volume target against verbalized
  confidence**. All of these are `abstract-checked`, not `verified`; the run remains gated on primary-source
  verification of arXiv:2406.15927 (binarized-target confirmation) and arXiv:2503.14749 by a named reader, per the
  program's citation ceiling.

## Options considered

- **A single-turn "answer and confidence together" elicitation for B1** — rejected: joint answer-and-confidence is
  the known-overconfident format (arXiv:2505.23845), and folding the confidence into the answer turn couples the
  parse to the answer text. The two-turn form gives B1 its strongest simple footing, which is required for a probe
  win to mean anything.
- **Sampling the confidence utterance instead of greedy decode** — rejected: sampling would add draw variance to
  the baseline the probe is measured against, contaminating the comparison with sampler noise unrelated to the
  model's expressed confidence.
- **Dropping unparseable B1 items silently, or looping retries until parse** — rejected both ways: silent dropping
  selects the comparison set on the baseline's own failure mode; unbounded retries manufacture a parse. One
  identical retry then explicit missing-count is the honest middle, mirroring the program's count-and-report
  discipline for excluded items.
- **Comparing on raw calibration error (ECE/Brier) instead of AUROC** — not chosen as the headline metric: the
  protocol frames the downstream test as **correctness prediction**, for which AUROC over the answerable subset is
  the discrimination metric that is comparable across arms with different native scales. Calibration metrics may be
  reported alongside but are not the pre-registered comparison.
- **Omitting B4 (the direct correctness probe)** — rejected: without a probe trained directly on correctness, a
  volume-probe win could not be separated from "correctness is just linearly readable from the state anyway." B4 is
  the control that isolates the value of the volume-target framing.

## Consequences

Fixes four comparators and one comparison procedure so that the protocol's "beats verbalized confidence" condition
is decided by a pre-registered AUROC-with-paired-bootstrap test over a fixed answerable subset, not by inspection.
The cost is that B1 is frozen as a **single** verbalized elicitation: a reviewer can object that a differently
worded or SFT-strengthened (arXiv:2503.14749) verbalized arm might beat the probe where this one does not, and that
objection is legitimate — the record answers it only by freezing the strongest *simple* form and citing the
stronger conceivable one, not by testing every phrasing. The narrow edge is a deliberate constraint: E3 does not
claim novelty against the crowded verbal-vs-sampling literature, only against the specific single-forward-pass
continuous-volume-probe-vs-verbalization head-to-head, and the record states that boundary exactly so a confirmed
result is not over-read.
