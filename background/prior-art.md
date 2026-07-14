# Prior-Art Map

What is already covered by existing work (and therefore credited, not claimed), what is partially covered (with the open edge stated), and what is absent from the literature. Compiled 2026-07-13; per-citation verification status in [../VERIFICATION.md](../VERIFICATION.md). This map is a set of claims about the public record — re-checkable by anyone, and corrections are welcome as pull requests.

## Covered — established results this program builds on

| Program element | Established work |
|---|---|
| Grounding by intervention (remove source, observe change) | ContextCite (NeurIPS 2024), AttriBoT, ARC-JSD — log-prob-based leave-one-out attribution |
| Prompt sensitivity as a measurable failure | Sclar et al. (ICLR 2024): up to 76pp swings from formatting; ProSA: instance-level sensitivity |
| Output-distribution clustering for uncertainty | Semantic entropy (Farquhar et al., Nature 2024) |
| Hidden states carry uncertainty information | Semantic Entropy Probes (arXiv:2406.15927); P(IK); behavior prediction from input states (arXiv:2502.13329) |
| Belief states linearly represented in the residual stream | Shai et al. (arXiv:2405.15943) — small transformers, synthetic HMM data |
| Trajectory-based hallucination detection | arXiv:2510.04933 (AUROC 0.959), 2606.01033, 2507.16488 (ICR Probe, ACL 2025), 2502.03199 |
| Hallucination as attractor/basin dynamics | arXiv:2604.15400 (causal patching), 2604.04743; energy-landscape variants 2508.14496, 2602.18671 |
| Contraction-shape of sampled entropy predicts reliability | arXiv:2603.18940, 2604.06192 |
| Continuous semantic-dispersion metric (endpoint) | Semantic Volume, arXiv:2502.21239 |
| Instructed forgetting/disregard leaves contamination | arXiv:2410.00382, 2506.08184, 2602.04288, 2605.08563, 2505.15392, 2412.06593, 2605.30219, 2406.19764 |
| Decode-time semantic constraint enforcement | SEM-CTRL (2503.01804), Token-Guard (2601.21969), SMC steering (2306.03081, 2504.13139) |
| Conservation laws for transformer *training* dynamics | Marcotte et al. (ICML 2025, 2506.06194) |
| Residual-stream depth dynamics (non-conservation framing) | arXiv:2502.12131, 2605.14258 |
| Factor analysis over LLM evaluation matrices | arXiv:2507.20208 (capability benchmarks) |
| Deterministic resolution beats LLM judgment (freshness) | arXiv:2606.01435 (+10–21pp) |
| Architectural ambiguity-preservation mechanism | NRR-Core/NRR-Phi (2512.13478, 2601.19933 — unreviewed preprints, 2-arm evaluation) |
| One constraint model, two enforcement layers (sequential) | ATLAS (arXiv:2510.25890 — schema validity, pipeline composition) |

## Partially covered — the open edge, per hypothesis

| Hypothesis | What exists | What does not |
|---|---|---|
| H-PC (premature closure) | Detection; attractor framing; step-level commitment; the contested direction itself | Settling-depth **coupled to evidence incorporation**; a regime-separating study |
| H-VOL (future volume) | Binarized probe; step-resolved sampled contraction; endpoint volume metric | Continuous regression target from the latent state; verbalized-confidence baseline; belief-state connection at LLM scale |
| H-ENF (enforced preservation) | An architectural enforcer vs unconstrained baseline | The 3-arm causal isolation of enforcement over instruction, on unmodified models |
| H-REL (reclosure) | The failure of instruction, replicated ≥7×; a 2-arm deterministic-resolver result; a product's unverified AGM claim | The 3-arm comparison with a mechanical contraction arm and downstream contamination as outcome |

## Absent from the literature (verified by search, as of 2026-07-13)

- Any systematic search for quantities conserved along inference depth in transformers (H-INV / E2) — and any linkage of invariant violation to behavioral failure.
- Any statement — let alone test — of lowering invariance for semantic specifications (H-IR / E6): same spec, independent enforcement backends, verdict agreement.
- Any factor-analytic test of whether structural-quality measurements collapse to one latent (H-SCALAR / E0). The single candidate (arXiv:2605.08522) was withdrawn by its authors.
- The term and operation "reclosure" (programmatic contraction + regeneration as revision semantics) — zero hits under any phrasing tried.

## Known discrepancies and cautions

1. Two independent readings of arXiv:2604.15400 during the review described its method differently (generation-step bifurcation vs layer-wise KL). Resolve against the primary source before citing its specifics.
2. NRR-Core/NRR-Phi and the XTrace product are unreviewed sources treated as novelty threats, not as settled results.
3. ReviseQA (OpenReview) was inaccessible during the review; its methodology may overlap E5's task design.
