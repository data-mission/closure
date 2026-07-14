# E4 — Enforced ambiguity preservation

**Question:** For genuinely ambiguous inputs, does **mechanically enforcing** that the output covers the true interpretation set outperform **instructing** the model to preserve ambiguity?

**Hypothesis:** [H-ENFORCE](../../HYPOTHESES.md#h-enforce--preservation-must-be-enforced-not-requested). Not gated on E0 — a failure retires enforcement as an operator, nothing broader.

## Status and prior art

`PARTIALLY PRE-EMPTED` — the strong form ("nobody has built an enforcement mechanism") is false; the causal comparison is open:

- An architectural enforcement mechanism exists: NRR-Core (arXiv:2512.13478) and NRR-Phi (arXiv:2601.19933) — multi-vector embeddings plus non-collapsing attention, reporting entropy retention of 0.91 vs 0.15 bits against an unconstrained baseline on a synthetic two-turn task. Caveats that matter for interpretation: single-author, unreviewed, heavy revision churn, and — critically — a **two-arm** comparison with no instructed-preservation arm. These are competing prior art and must be cited and differentiated.
- The premise that instruction alone is weak is independently published: instructed uncertainty-hedging misaligns with the model's intrinsic uncertainty (arXiv:2405.16908); enumerate-interpretations prompting exists as a pure instruction-level method (arXiv:2511.10453).
- Coverage metrics exist: ambiguous-QA benchmarks report existing methods generate ~1.17 interpretations per question against ~2.19 in ground truth (arXiv:2511.01323, arXiv:2502.01523) — reusable as the outcome measure.
- No paper runs the three-arm design isolating the causal contribution of enforcement over instruction, on unmodified production models.

Citation statuses: [VERIFICATION.md](../../VERIFICATION.md).

## Protocol

1. **Corpus.** Queries with annotated ambiguity structure: ambiguous-QA style (known interpretation sets) plus conflicting-source tasks (documented disagreements between provided sources).
2. **Arm A — plain.** Standard generation.
3. **Arm B — instructed.** Explicit instruction to identify and preserve all valid interpretations / source disagreements.
4. **Arm C — enforced.** Mechanical pipeline on the same unmodified model: first map the interpretation space (repeated-generation clustering — the P measurement used as a *mechanism*), then constrain the final generation to represent each discovered cluster (structured output schema over the cluster set, or decode-time constraint). No architecture changes — this is also the only deployable form for closed models.
5. **Score.** Interpretation-set retention: coverage of the annotated set + penalty for fabricated interpretations, using the published coverage metrics.

## Verdict conditions (pre-registered)

- **CONFIRMED** iff C substantially exceeds B on retention (B vs A quantifies how much instruction buys; C vs B isolates enforcement).
- **REFUTED** iff B ≈ C — instruction suffices, and `preserve` is demoted from operator to diagnostic in the registry.

## Cost and prerequisites

API-only against production models; clustering machinery shared with the P measurement. No GPU.

## Exclusion criteria (pre-registered)

Excluded before any arm runs, counted and reported: queries whose annotated interpretation set is disputed by adjudicators. Exclusions are decided once and applied identically to all three arms — no per-arm exclusion is permitted.

## Wanted from contributors

- The enforcement pipeline (cluster → constrained regeneration) as a clean reference implementation.
- Corpus curation with adjudicated interpretation sets.
- A fair-instruction red-team: the strongest possible Arm B prompt, so a C-win can't be attributed to a strawman instruction.
