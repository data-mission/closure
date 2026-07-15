# e3-0001 — Probe class, input vector, regression target, and evaluation regimes

- Status: proposed
- Deciders: closure research program contributors
- Scope: E3

This record is e3-scoped pending a merge-time renumbering into the global `decisions/` sequence (see
`README.md` in this directory).

## Context

The E3 protocol (`../README.md` § Protocol step 2) says "train a linear probe on the single pre-sampling hidden
state to **regress** [semantic] volume." It fixes the probe as linear, the target as continuous volume, and the
input as the pre-sampling state — but leaves open which linear estimator, how it is regularized, exactly which
tensor the input vector is, how features are standardized, and how the probe is evaluated. Each is a choice that
moves the reported R², Spearman, and OOD numbers, so each must be fixed before any real hidden state is extracted.
The volume statistic that supplies the target is fixed separately in e3-0002; this record fixes the map from the
latent vector to that target.

## Decision

- **Input vector.** The final-layer hidden state at the last prompt token, after the final RMSNorm and immediately
  before the `lm_head` projection — the pre-sampling state. Extraction point, verified against the installed source
  in `../FEASIBILITY.md`: in mlx-lm 0.31.3 `mlx_lm/models/qwen2.py`, `Qwen2Model.__call__` returns `self.norm(h)`
  (post-final-norm hidden states, shape `(B, L, 3584)`) and `Model.__call__` applies the head to that output, so
  `model.model(ids)[:, -1, :]` **is** the vector the head reads and no logits/hidden ambiguity exists in this API.
  The prompt is chat-templated and run as a single forward pass with **no generation**. Hidden dim is 3584; the
  float16 activation is cast to float32 for all probe arithmetic. That this is the true pre-sampling state — not a
  pre-norm, wrong-layer, or wrong-position tensor — is established by the 20/20 lm_head top-1 sanity check recorded
  in `../FEASIBILITY.md`: projecting the extracted vector through the head reproduces the exact top-1 next-token id
  of the full forward pass for all 20 spike prompts (max abs logit difference 0.03125, argmax identical in every
  case). The model is pinned in e3-0004: `mlx-community/Qwen2.5-7B-Instruct-4bit`, snapshot revision
  `c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed`, mlx-lm 0.31.3.

- **Probe class: ridge regression (linear, closed-form).** Linearity is not a convenience — it *is* the hypothesis.
  H-VOL states that volume is "decodable by a linear probe"; a nonlinear probe would test a different and weaker
  claim (that the information is *present*, not that it is *linearly readable*). Ridge is the linear estimator
  chosen because the input dimension d = 3584 is large relative to any corpus-scale n this program can afford to
  sample ground truth for (e3-0002 cost projection: hundreds to ~1000 prompts), so an unregularized fit is
  ill-posed. The closed-form ridge solution on a fixed feature matrix is deterministic, which is what makes the
  probe fit exactly reproducible under e3-0004.

- **Regularization strength.** `alpha` is selected by inner k-fold cross-validation **on the training split only**,
  over a pre-registered log-spaced grid. The grid and fold count are fixed in the frozen config (e3-0004) before
  any real data is fit; `alpha` is never re-chosen after seeing held-out or OOD performance. Selecting `alpha` on
  the training split alone is the leakage guard for the regularizer itself.

- **Target: log semantic volume, per e3-0002.** The regression target is the log of the Gram-determinant volume
  statistic defined in e3-0002, not the raw determinant. Log because Gram determinants of near-degenerate to
  well-spread continuation sets span orders of magnitude, and a linear probe against a raw multiplicative-scale
  target would be dominated by a few extreme prompts. The log transform is pre-registered here, chosen from the
  determinant's known dynamic range — not selected after inspecting the empirical distribution of volumes.

- **Feature standardization.** Features are z-scored (mean/variance per hidden dimension) with the mean and
  variance **estimated on the training split only** and applied unchanged to every evaluation split, including OOD.
  Fitting the standardizer on any data the probe is later scored against would leak held-out and OOD statistics
  into the probe input; the train-only fit is named here as the explicit leakage guard.

- **Two evaluation regimes.** (a) **In-distribution:** held-out prompts drawn from the same task families as
  training, scored by R² and Spearman rank correlation between predicted and ground-truth log volume — this is the
  regression-fidelity number of README Evaluation (a). (b) **Out-of-distribution, load-bearing:**
  leave-one-task-family-out — the probe is trained on all families but one and evaluated on the held-out family,
  rotated over every family. This is the discriminating test of README Evaluation (c): the belief-state reading of
  H-VOL implies a geometric encoding that should transfer across task families, whereas a probe that found a
  dataset-specific shortcut will collapse when a whole family it never saw is the test. OOD generalization, not
  in-distribution R², is the load-bearing result.

## Options considered

- **MLP / nonlinear probe** — rejected: it tests a different hypothesis. A nonlinear probe succeeding would show
  the volume information is *present* in the state, which is weaker than and not the claim H-VOL makes ("decodable
  by a **linear** probe"). Admitting a nonlinear probe as the primary instrument would let the record confirm
  something the protocol did not register.
- **Unregularized OLS** — rejected: with d = 3584 features and an n bounded by ground-truth sampling cost, OLS is
  ill-posed and overfits; ridge is the honest linear default at this d/n ratio, and its closed-form solution is
  what e3-0004 relies on for exact reproducibility of the fit.
- **Classification on binarized (high/low) volume as the primary probe** — rejected as primary: that is exactly
  what Semantic Entropy Probes (arXiv:2406.15927) already demonstrated. Making it primary would re-run known work
  and forfeit E3's only novel claim (continuous regression target). It survives only as a **baseline** — the
  SEP-style binarized companion probe — and is specified in e3-0003, not here.

## Consequences

Fixes the probe as a deterministic, regularized linear map from a single named pre-sampling vector to log volume,
evaluated under a fidelity regime and a transfer regime. The single highest-exposure choice is committing to a
**linear** probe: it deliberately trades away any predictive power that lives in nonlinear structure of the hidden
state, because reading that structure would answer a different question than the one registered. If the linear
probe fails in-distribution, that is a real result about linear decodability, not a tooling shortfall — and the
protocol's REFUTED branch ("signal exists only at binary granularity, or fails OOD, or adds nothing over verbalized
confidence") is where a linear-but-binary-only outcome lands. The leave-one-family-out regime is costly (the probe
is refit once per family and every family must be populated well enough to train on the rest), and it will report a
lower number than in-distribution held-out; that lower number is the intended headline, not a regression to be
tuned away.
