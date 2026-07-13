# E1 — Premature closure

**Question:** When a model hallucinates, did its state settle **before** incorporating the retrieved source — and does separating settling-depth from step-commitment and basin-stability reconcile the contradiction in the published literature?

**Hypothesis:** [H-PC](../../HYPOTHESES.md#h-pc--hallucination-is-premature-closure).

## Status and prior art

`CONTESTED` — the most crowded neighborhood in the program, which is exactly why the scope must be precise:

- **Detection is done.** Layer-trajectory hallucination detectors already beat semantic entropy (arXiv:2510.04933 reports AUROC 0.959; also 2606.01033, 2502.03199, 2507.16488). Do **not** run another detection study.
- **The direction is contested.** arXiv:2604.15400 finds hallucination = *early* commitment to a stable-but-wrong attractor (with causal patching); arXiv:2602.09825 and 2507.06722 find hallucination = *late*-layer instability / failure to settle; 2510.04933 finds settling velocity inert (d≈0.01) but convergence depth discriminative. These cannot all be the whole story.
- **The coupling is unmeasured.** No paper asks whether early settling co-occurs with the source *not being read* before the state froze.
- The original hypothesis conflates three things that this design must separate: (a) settles earlier in **depth** (layers), (b) commits earlier in **step** (token position — already shown: 2604.15400, 2605.24396, 2603.01437), (c) settles into a more **stable basin** (already shown: 2604.15400, 2604.04743). The open claim is (a) **coupled to constraint-non-incorporation**.

Citation statuses: [VERIFICATION.md](../../VERIFICATION.md). One discrepancy to resolve at the primary source before publication: two independent readings of 2604.15400 describe it differently (step-level bifurcation vs layer-KL trajectory).

## Instruments (verified to exist — do not reinvent)

- **Settling:** CLSS_l = 1 − JSD(φ(h_l), φ(h_{l−1})) → the layer where the token distribution stops moving. φ = **tuned-lens projection as primary** (raw logit lens is known-unfaithful on many models; a plateau can be an unembedding artifact, not computation); 2602.09825's original logit-lens variant as robustness check.
- **Constraint incorporation:** ICR = JSD(Proj_i^l, Attn_i^l) — whether a layer's update is attention/context-driven vs FFN/parametric-driven (ICR Probe, 2507.16488, ACL 2025) → the "was the source read" signal.
- **Discrete cross-check:** saturation/rank-fixation events across layers (2410.20210 — currently has zero hallucination correlation attached; any found is new).
- **Second axis:** latent displacement under small late-context perturbations (paraphrase/reorder) — stability measurement for the regime clustering.
- **Mechanism prior:** ReDeEP (2410.11414) — RAG hallucination as FFN over-weighting parametric knowledge while copying heads fail to integrate retrieved content.

## Protocol

1. Open-weights model with hidden-state access. RAG task set with known ground-truth sources.
2. **Label** each output faithful vs hallucinated using the leave-one-out grounding test as oracle (the program's verification tooling produces these labels). Ordering dependency, stated plainly: E0 independently examines this oracle's construct validity, so run E0 first; a weak E0 outcome propagates into E1's labels, which then stand on the LOO test's own validation, not on closure.
3. Per generation, per layer, record: settling layer (CLSS plateau), ICR timing (when/whether the source was incorporated), saturation layer, perturbation displacement.
4. **Primary comparison:** settling-layer and ICR-timing distributions, faithful vs hallucinated.
5. **Regime analysis:** cluster hallucinations in the (settling depth × stability/displacement) plane. The two-regime hypothesis: hallucinations bifurcate into *early-settled-wrong* and *never-settled*, and the contradictory published findings each saw one regime through a metric blind to the other.

## Verdict conditions (pre-registered)

- **PREMATURE CLOSURE HOLDS** iff hallucinated outputs settle **≥ 3 layers earlier** than faithful ones (p < 0.01) AND ICR shows the source was not incorporated before the settling layer.
- **Two-regime secondary:** hallucinations occupy ≥ 2 separable regions while faithful outputs occupy a third (settled-late-and-stable) — reconciling the published contradiction; report per-regime detection performance.
- **DIES** iff hallucinated settling is same-or-later (the late-instability picture wins) OR settling depth is uncorrelated with ICR timing. This experiment is allowed to lose — either outcome resolves a real tension the field currently has.

## Cost and prerequisites

Open model (7B–70B class), logit-lens/tuned-lens tooling, single-digit GPU-days for ~500–1000 labeled claims. Depends on the verification tooling for labels.

## Exclusion criteria (pre-registered)

Excluded before internals analysis, counted and reported: generations where the LOO oracle's faithful/hallucinated label is ambiguous (label confidence below a pre-set threshold); runs with layer-recording failures. Never excluded: any generation based on its settling or ICR values — the metrics under test cannot select the sample.

## Wanted from contributors

- CLSS + ICR reimplementation as a clean per-layer recording harness.
- The labeled faithful/hallucinated RAG dataset (built with the LOO oracle).
- Resolution of the 2604.15400 reading discrepancy against the primary source.
