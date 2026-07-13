# E2 — Conservation laws of the forward pass

**Question:** Do non-trivial quantities exist that are conserved along the depth of a single inference forward pass — and does their violation coincide with behavioral failure classes?

**Hypothesis:** [H-INV](../../HYPOTHESES.md#h-inv--the-forward-pass-has-conservation-laws).

## Status and prior art

`OPEN` — both halves unattempted, verified by direct search:

- Conservation laws have been derived for transformer **training** dynamics (gradient-flow parameter symmetries: Marcotte, Gribonval, Peyré, ICML 2025, arXiv:2506.06194). That is a different object — conservation across optimization steps, not along inference depth.
- The closest empirical work treats the residual stream as a dynamical system (arXiv:2502.12131: cross-layer unit continuity, attractor-like dynamics; arXiv:2605.14258: full Jacobian eigendecomposition across three production-scale models, a learned monotonic spectral gradient through depth) — real depth-dynamics analysis, never framed as conservation, never linked to failures. Their instrumentation is directly reusable here.
- Architectural invariant-subspace results (arXiv:2602.09783, ICML 2026) are static structural claims; a conserved quantity is the dynamical strengthening of that kind of claim.
- Automated conserved-quantity discovery from trajectory data exists as a method family (Liu & Tegmark's "AI Poincaré" line) and has never been pointed at a transformer's own inference dynamics.
- Zero papers link any depth-invariant's breaking to contradiction, instruction-drop, or hallucination.

Citation statuses: [VERIFICATION.md](../../VERIFICATION.md).

## Protocol

1. **Collect trajectories.** Open-weights model; residual-stream states h_l at every layer, at selected token positions, over a large and diverse prompt corpus (varied domains, lengths, task types).
2. **Normalize out known dynamics first.** Residual norm growth and the depth-wise spectral gradient (2605.14258) are established; any "invariant" that is an artifact of them is trivial by construction. Work in normalized coordinates.
3. **Run discovery.** Two independent routes, cross-checked: (a) learned invariants — train f(h) to be constant along trajectories while non-constant across them (AI-Poincaré-style objective); (b) symbolic regression over simple functionals (subspace projections, angle/ratio families, entropy-like quantities).
4. **Validate candidates.** An invariant must hold across prompts (not per-prompt constants), across positions, and survive held-out data. Report conservation error distributions.
5. **Behavioral linkage.** On labeled failure datasets (contradiction, instruction-drop, hallucination — the last produced by the program's grounding oracle), test whether failure cases show significantly larger invariant violation than matched non-failure cases.

## Verdict conditions (pre-registered)

- **CONFIRMED** requires both: (i) at least one non-trivial invariant holding across prompts, and (ii) at least one invariant whose violation separates a failure class from matched controls at conventional significance with a meaningful effect size.
- **REFUTED** if all discovered quantities are trivial (artifacts of normalizable dynamics) or behaviorally inert. In that case the "native invariants" hypothesis of the founding concept is demoted from physics to vocabulary, and the registry says so.

## Cost and prerequisites

The most expensive and highest-risk experiment in the program: open model, trajectory storage at scale, discovery-method engineering. Run when the measurement tooling and labeled failure datasets already exist. Flagship result if positive — it would be the first conservation law of transformer inference.

## Exclusion criteria (pre-registered)

Excluded, counted and reported: trajectories with numerical instabilities (NaN/overflow). Never excluded: prompts based on how discovered candidate invariants behave on them — invariants must survive the corpus as pre-registered, not a corpus curated to fit them.

## Wanted from contributors

- Trajectory collection harness with efficient storage (this is an infrastructure contribution reusable by E1).
- Implementation of the two discovery routes with a shared validation interface.
- Skeptical review of the triviality criteria *before* discovery runs — the pre-registration of what counts as "non-trivial" is where this experiment is won or lost.
