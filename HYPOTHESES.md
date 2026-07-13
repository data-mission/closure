# Hypothesis Registry

Every claim of the program, each with its **status**, **kill condition**, and **experiment**. Statuses: `OPEN` (untested, no prior work), `CONTESTED` (field has contradictory findings), `PARTIALLY PRE-EMPTED` (a component exists in prior work; the open edge is stated), `RETIRED` (killed under scrutiny — kept visible), `CONVERGENT` (independently published by others; now prior art, priority not claimable).

Novelty statuses reflect a literature check against 2024–2026 work (as of 2026-07-13) — every status is a claim about the public record and can be re-checked by anyone. Provenance of the review and per-citation verification status: [VERIFICATION.md](VERIFICATION.md).

Each active hypothesis also carries a **confidence** line in IPCC calibrated language (*very low / low / medium / high / very high*, derived from evidence quality and agreement across sources — see [METHODOLOGY.md](METHODOLOGY.md)). Confidence is a different axis from status: status describes the state of the literature; confidence is our current credence that the claim will hold, stated so its movement over time is auditable.

---

## Active hypotheses

### H-CORE — Closure exists
**Claim:** Grounding (G), rigidity (R), and ambiguity-preservation (P) scores of an AI output are noisy readouts of ONE latent property — closure quality — not three independent measurements.
**Why it matters:** This is the existence test for the program's central object. If true, a composition/specification layer over the tests is principled. If false, "closure" is a metaphor over four unrelated functions, and this page will say so.
**Status:** `OPEN` — the instrument (exploratory factor analysis + parallel analysis on score matrices) exists and was validated on capability benchmarks (arXiv:2507.20208); nobody has run it on structural-quality axes. The one candidate pre-emption (arXiv:2605.08522) was withdrawn by its own authors citing a fatal flaw.
**Confidence it holds:** low — plausibility arguments and the founding derivation only; no direct evidence in either direction. That is what makes it the right gate: cheap, decisive, unprejudged.
**Kill condition:** pairwise |r| < 0.2 between G/R/P across 100–200 tasks, no dominant factor above the parallel-analysis threshold — or the shared factor vanishing after controlling for task difficulty.
**Experiment:** [E0](experiments/E0-closure-existence/)

### H-PC — Hallucination is premature closure
**Claim:** Hallucination = the residual stream settles into a stable configuration at an earlier layer specifically **because** a provided constraint (the retrieved source) was not incorporated before settling. "Local consistency reached before global consistency."
**Why it matters:** A mechanical, causal definition of hallucination — a computational event you can measure, not a linguistic judgment after the fact.
**Status:** `CONTESTED` — the detection layer is crowded (trajectory-based detectors already beat semantic entropy), but published papers *disagree on the direction*: one line finds hallucination = early commitment to a stable-but-wrong attractor; another finds late-layer instability. Nobody measures the coupling to constraint incorporation. The original statement of this hypothesis predates the attractor papers.
**Confidence it holds:** low — published evidence points in *both* directions (early-commitment vs late-instability); the coupling that would decide it is untested.
**Kill condition:** hallucinated outputs settle at the same or later layer than faithful ones, OR settling depth is uncorrelated with whether the source was incorporated (ICR timing). Losing to the late-instability picture is an admissible outcome — and would itself resolve the field's contradiction.
**Experiment:** [E1](experiments/E1-premature-closure/)

### H-INV — The forward pass has conservation laws
**Claim:** There exist non-trivial quantities conserved along the depth of a single inference forward pass, and their violation coincides with behavioral failure classes (contradiction, instruction-drop, hallucination).
**Why it matters:** If invariants of the native evolution exist, interpretability gains its first conservation laws — the most fundamental kind of structure a dynamical theory can have.
**Status:** `OPEN` — zero prior work on both halves. The nearest results are conservation laws of *training* dynamics (a different object) and dynamical-systems analyses of the residual stream that never use conservation framing and never link to failures.
**Confidence it holds:** very low — no evidence exists; pure hypothesis with an available instrument. Highest risk, highest payoff in the program.
**Kill condition:** automated conserved-quantity discovery over residual-stream trajectories yields only trivial invariants (normalizable dynamics like norm growth) or invariants with no behavioral correlate.
**Experiment:** [E2](experiments/E2-conserved-quantities/)

### H-VOL — Confidence is the volume of reachable futures, readable from the latent state
**Claim:** The semantic diversity of a model's possible continuations is a **continuous** quantity encoded in the pre-sampling hidden state — decodable by a linear probe in one forward pass, no sampling — and it beats the model's verbalized confidence as a predictor of correctness.
**Why it matters:** Grounds "confidence" in geometry rather than self-report; standalone payoff is a calibrated uncertainty estimator at a fraction of sampling cost.
**Status:** `PARTIALLY PRE-EMPTED` — the probe mechanism exists (Semantic Entropy Probes predict a *binarized* entropy class pre-generation); the step-resolved *contraction-shape* phenomenon was published independently in 2026 (see § Independent convergence below). Open edge: continuous volume as regression target + head-to-head vs verbalized confidence + the belief-state-geometry bridge at LLM scale. The "volume of reachable futures" framing has no prior use.
**Confidence it holds:** medium — the binarized version of the signal is demonstrated (Semantic Entropy Probes); the open question is whether the continuum and the geometry are there too.
**Kill condition:** the hidden state encodes only the binary high/low class (already known), or the probe fails to generalize out-of-distribution, or adds nothing over verbalized confidence.
**Experiment:** [E3](experiments/E3-future-volume/)

### H-ENF — Preservation must be enforced, not requested
**Claim:** For genuinely ambiguous inputs, mechanically enforcing that the output represents the full interpretation set beats *instructing* the model to preserve ambiguity — the model is otherwise not able to keep uncertainty from collapsing into fluency, even when asked.
**Why it matters:** Decides whether `preserve` is an operator (runtime mechanism) or a diagnostic (measurement) — the first test of the concept's actuation half.
**Status:** `PARTIALLY PRE-EMPTED` — an architectural enforcement mechanism exists in unreviewed single-author preprints (NRR-Core/NRR-Phi), compared only against an unconstrained baseline. The controlled 3-arm comparison (plain vs instructed vs enforced) isolating the causal contribution of enforcement, on unmodified production models, is unrun. The premise (instructed uncertainty expression misaligns with actual uncertainty) is independently published.
**Confidence it holds:** medium — an architectural enforcer beats an unconstrained baseline in unreviewed preprints, and instruction is independently documented as weak; the causal isolation is missing, not the direction.
**Kill condition:** instructed ≈ enforced on interpretation-set retention — instruction suffices, the enforcement layer is ceremony.
**Experiment:** [E4](experiments/E4-enforced-ambiguity/)

### H-REL — Revision is an operation, not a request
**Claim:** When evidence contradicts an earlier assumption, programmatically rebuilding the context **without** the assumption (an explicit contraction operation in the sense of AGM belief revision) reduces downstream contamination far more than instructing the model to disregard it.
**Why it matters:** The `release` operator and revision rules earn existence with a quantified effect size; agent pipelines gain a principled alternative to "append a correction and hope."
**Status:** `PARTIALLY PRE-EMPTED` — the premise (instructed disregard leaves contamination) is proven independently at least seven times, including at the representation level ("models pretend to forget": the final layer says forgotten while earlier layers still compute from the content). The 3-arm comparison with mechanical rebuild as the third arm and downstream-conclusion contamination as the measured outcome is unrun. Note: a commercial product (XTrace) claims AGM operations at runtime — unverified marketing, no published experiment; "first to apply AGM" is not claimable, "first controlled comparison" is.
**Confidence it holds:** high — the premise (instruction leaves contamination) is replicated at least seven times, and the closest two-arm analog shows a +10–21pp mechanical advantage; only the controlled three-arm isolation is missing.
**Kill condition:** instructed-disregard ≈ mechanical rebuild on downstream contamination.
**Experiment:** [E5](experiments/E5-reclosure/)

### H-IR — Structural specs are a real abstraction (lowering invariance)
**Claim:** The same structural specification ("claims grounded in sources", "conclusions rigid under paraphrase") lowered onto two **independent** enforcement backends — post-hoc verification and decode-time enforcement — produces agreeing verdicts. Implementation-independent semantics is what makes a specification layer an intermediate representation rather than a collection of tools.
**Why it matters:** This is the falsifiable form of the entire "compiler for AI computation" idea. SQL became an abstraction because the same query means the same thing on every engine.
**Status:** `OPEN` — the claim has never been stated in the literature. Both backend types exist separately; the one system that compiles one constraint model to two layers runs them sequentially (generate-then-validate) and never compares verdicts.
**Confidence it holds:** low — never tested by anyone; both backends exist separately and nothing is known about their agreement. Genuine white space cuts both ways.
**Kill condition:** verdict agreement < 70% across lowerings, or disagreements unsystematic (pre-registered bands: ≥ 85% agreement with κ ≥ 0.7 confirms). (A *systematic* disagreement taxonomy would be a publishable finding in its own right: a map of where "the same property" means different things at different enforcement points.)
**Experiment:** [E6](experiments/E6-lowering-invariance/) — with an expressiveness A/B (E6b) gated on E0 and E6 both passing.

### H-COMP — Composed checks catch what isolated checks miss
**Claim:** Pipelines composing the tests (grounding feeding ambiguity-checking feeding collapse-detection) catch real failures that no individual test catches.
**Why it matters:** Decides "system" vs "library" for the measurement layer.
**Status:** `OPEN` — designed in the program's prior corpus (30–60 tasks, three adversarial task types), unrun. Interpret in light of E0: E0 tests whether one *object* underlies the tests; this tests whether *composing* them adds detection power.
**Confidence it holds:** low — the program's own earlier adversarial review left this contested; designed to be settled, not assumed.
**Kill condition:** fewer than 5 composition-only catches across the battery, or catches not confirmed by human review.
**Experiment:** [E7](experiments/E7-composition/)

---

## Independent convergence (now prior art)

Ideas from the founding concept that others published independently in 2026. They are prior art; priority cannot be established from private records and is not claimed. Their value here is directional only — the open edges past them are stated in E1 and E3. (Context: [background/reduction-history.md](background/reduction-history.md).)

| Idea (as originally stated) | Independent publication |
|---|---|
| Hallucination as settling into a stable-but-wrong attractor basin | Trajectory-commitment and hallucination-basin papers, 2026 |
| Reasoning as progressive contraction of the reachable-future space, with the contraction *shape* predicting reliability | Entropy-trajectory-shape and stepwise-informativeness papers, Mar–Apr 2026 |

## Retired claims

Killed under adversarial scrutiny in the program's earlier phase. Kept visible; do not resurrect without new evidence.

| Claim | Why it died |
|---|---|
| "This is a new computational paradigm" | The falsifiable content is the hypotheses above, not a paradigm assertion. Argue results, not category. |
| "The six operators form a complete algebra" | The operator set grew 50% under five test tasks; `stabilize` had no operational definition; no domain axiomatization exists. The operators are a working vocabulary, not a proven algebra. |
| "Convergent design" (independent artifacts converging on the operators) | Same author designed both artifacts; post-hoc pattern matching; unfalsifiable as claimed. |
| "Closure" justified by formal fixed-point mathematics | The mathematics was never formalized. The concept now stands on *empirical* legs (E0, E1) — and one *positioning* leg: closure is an equilibrium concept (DEQ/Hopfield/energy-based lineage), not Design by Contract; see [background/closure-vs-dbc.md](background/closure-vs-dbc.md). |
