# E3 — Future volume from the latent state

**Question:** Is the semantic diversity of a model's possible continuations a **continuous** quantity encoded in the pre-sampling hidden state — decodable by a linear probe in one forward pass — and does it beat verbalized confidence as a correctness predictor?

**Hypothesis:** [H-VOL](../../HYPOTHESES.md#h-vol--confidence-is-the-volume-of-reachable-futures-readable-from-the-latent-state).

## Status and prior art

`PARTIALLY PRE-EMPTED` — the scoping here is strict, because two adjacent literatures each own a piece:

- **The probe mechanism is established.** Semantic Entropy Probes (Kossen et al., arXiv:2406.15927, ICLR 2025): linear probes on hidden states — including a token-before-generation variant — predict a **binarized** (high/low) semantic-entropy class, beating naive entropy, log-likelihood and p(True). Ashok & May (arXiv:2502.13329, NeurIPS 2025) extend pre-generation probing to behavior prediction. E3 cannot and does not claim the mechanism.
- **The step-resolved contraction phenomenon is established.** Sampled entropy trajectories over reasoning prefixes predict reliability (arXiv:2603.18940: monotone-contraction 68.8% vs non-monotone 46.8% accuracy, p = 0.0005; arXiv:2604.06192 adds shape taxonomy and theory). This is the sampling-based, step-resolved half of the idea — published.
- **A continuous volume metric exists, endpoint-only.** Semantic Volume (arXiv:2502.21239): Gram-determinant over continuation embeddings.
- **What does not exist** (verified absent): a probe with the **continuous** volume as regression target; a head-to-head against **verbalized confidence**; and any connection of belief-state geometry (Shai et al., arXiv:2405.15943 — belief states linearly represented in the residual stream, shown on small transformers over synthetic HMMs) to uncertainty quantification in production-scale LLMs.

Pre-flight: two possibly-adjacent papers were flagged but not confirmed during the literature review (arXiv:2503.14749; a verbalized-confidence-vs-semantic-entropy comparison under matched compute) — check them before running. Citation statuses: [VERIFICATION.md](../../VERIFICATION.md).

## Protocol

1. **Ground truth.** Per prompt: sample N continuations, embed, compute the continuous semantic volume (Gram determinant per 2502.21239) — chosen over discrete answer-label entropy because it extends to open-ended tasks where answer labels don't exist.
2. **Probe.** Train a linear probe on the single pre-sampling hidden state to **regress** that volume (continuous target — not the high/low classification SEP already demonstrated).
3. **Baselines.** SEP-style binarized probe; correctness probes (P(IK)-style); the model's verbalized confidence; naive predictive entropy.
4. **Evaluation.** (a) Regression quality: R² / Spearman on held-out prompts. (b) Downstream: correctness prediction vs all baselines. (c) **OOD generalization** of the probe direction across task families — the belief-state interpretation implies a geometric encoding, not a dataset-specific artifact; this is the discriminating test between "probe found a shortcut" and "probe reads a real quantity."

## Verdict conditions (pre-registered)

- **CONFIRMED** iff the probe regresses continuous volume with useful fidelity, generalizes OOD, and beats verbalized confidence on correctness prediction.
- **REFUTED** iff the signal exists only at binary granularity (already known from SEP), or fails OOD, or adds nothing over verbalized confidence. Then "volume of reachable futures" is decoration over existing results and the registry says so.

Standalone value on confirmation: calibrated continuous uncertainty at single-forward-pass cost — no sampling at inference time.

## Cost and prerequisites

Open-weights model, embedding model, probe training (CPU-scale). Sampling for ground truth dominates cost at train time only.

## Exclusion criteria (pre-registered)

Excluded, counted and reported: prompts where ground-truth sampling fails to produce N valid continuations. Never excluded: items based on probe error — OOD and hard cases are the test, not noise.

## Wanted from contributors

- The ground-truth pipeline (sampling + Gram-determinant volume) as a reusable component.
- OOD task-family design — the generalization split is the scientifically load-bearing part.
- Pre-flight check of the two flagged papers.
