# Hypothesis Registry

Every claim of the program, each with its **status**, **kill condition**, and **experiment**. Statuses: `OPEN` (untested, no prior work), `CONTESTED` (field has contradictory findings), `PARTIALLY PRE-EMPTED` (a component exists in prior work; the open edge is stated), `RETIRED` (killed under scrutiny — kept visible), `CONVERGENT` (independently published by others; now prior art, priority not claimable).

**Governing rule.** Each experiment may directly retire only the claim it measures. Broader architectural claims survive, weaken, or die according to their explicitly documented dependencies and their own tests — no experiment directly kills a claim broader than the property it measures, and a downstream claim loses support only where it explicitly depends on a prerequisite that failed. This program's central object is multidimensional and typed ([the founding specification](CONCEPT.md#part-iv--the-specification-layer) is a tuple `C = (B, I, P, F, G, U, R, O)`, not a scalar), and its governance mirrors that: the claims form a lattice, not one all-or-nothing gate. What survives each result is read off the [consequence matrix](#consequence-matrix), not decided by a single verdict.

**The ontology's own exposure.** The trajectory ontology ([CONCEPT.md](CONCEPT.md) Parts I–II) is not exempt from the governing rule. Its empirical projections at the level it is stated — the native evolution — are exactly three: H-PC (E1), H-INV (E2), and H-VOL (E3); the behavioral hypotheses (E4–E8) neither confirm nor protect it. H-VOL's exploratory run currently supports it; nothing else does. Retirement condition, stated in advance: if E1 refutes, E2 refutes, and E3's registered replication refutes, the ontology loses every hidden-state projection and is demoted — on the record, in this file — from research-guiding hypothesis to interpretive vocabulary, joining the retired claims. The measurement instrument (G/R/P/F) is causal verification tooling on its own engineering merits and survives that retirement. The operational definitions connecting the two levels are in [background/formal-core.md](background/formal-core.md).

Novelty statuses reflect a literature check against 2024–2026 work (as of 2026-07-13) — every status is a claim about the public record and can be re-checked by anyone. Provenance of the review and per-citation verification status: [VERIFICATION.md](VERIFICATION.md).

Each active hypothesis also carries a **confidence** line in IPCC calibrated language (*very low / low / medium / high / very high*, derived from evidence quality and agreement across sources — see [METHODOLOGY.md](METHODOLOGY.md)). Confidence is a different axis from status: status describes the state of the literature; confidence is our current credence that the claim will hold, stated so its movement over time is auditable.

---

## Active hypotheses

### H-SCALAR — Grounding, rigidity, and ambiguity-preservation share one latent factor
**Claim:** G, R, and P scores of an AI output are noisy readouts of ONE scalar latent property — closure quality — not three independent measurements.
**Why it matters:** If true, the tests may be aggregated into a single closure score. If false, they are not one number and closure, if it survives, must be reported as a multidimensional profile. This is a claim about *scalar aggregation* — not about whether a structured closure specification exists (that is the structural lattice below, tested by E4–E7 and independent of this result).
**Status:** `OPEN` — the instrument (exploratory factor analysis + parallel analysis on score matrices) exists and was reported validated on capability benchmarks (arXiv:2507.20208; abstract-checked, per [VERIFICATION.md](VERIFICATION.md)); nobody has run it on structural-quality axes. The one candidate pre-emption (arXiv:2605.08522) was withdrawn by its own authors citing a fatal flaw.
**Confidence it holds:** low — plausibility arguments and the founding derivation only; no direct evidence in either direction. That is what makes it a cheap, decisive, unprejudged first measurement.
**Kill condition:** pairwise |r| < 0.2 between G/R/P across 100–200 tasks, no dominant factor above the parallel-analysis threshold — or the shared factor vanishing after controlling for task difficulty.
**Scope of the kill:** a negative result retires the single aggregate closure score, scalar aggregation of G/R/P, and the claim that closure quality is one-dimensional — **and nothing else.** It leaves the independent structural hypotheses (H-ENFORCE, H-RELEASE, H-COMPOSE, H-LOWER) logically open, and requires closure, if it survives, to be represented as a multidimensional structure rather than one number. Factor analysis has no power over the operators, composition, lowering, or the IR.
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
**First result (2026-07-15):** E3 executed — the program's first run. Verdict `confirmed-shaped` at the
pre-frozen thresholds: the probe regressed continuous volume (non-degenerate Spearman 0.83), survived
within-family and length-residualization controls, transferred under every leave-one-family-out rotation, and
beat verbalized confidence and predictive entropy on correctness prediction without being dominated by a
direct correctness probe. Two labels bind the claim: the run was **unregistered** (exploratory-grade by this
program's standard) and **threshold-fragile** on the length-residualization band. Confidence moves medium →
**high** on this evidence; the registered replication (second model, fresh corpus) is the step that would
settle it. Record: `experiments/E3-future-volume/run/VERDICT.md`; snapshot DOI 10.5281/zenodo.21383448.
**Experiment:** [E3](experiments/E3-future-volume/)

### H-ENFORCE — Preservation must be enforced, not requested
**Claim:** For genuinely ambiguous inputs, mechanically enforcing that the output represents the full interpretation set beats *instructing* the model to preserve ambiguity — the model is otherwise not able to keep uncertainty from collapsing into fluency, even when asked.
**Why it matters:** Decides whether `preserve` is an operator (runtime mechanism) or a diagnostic (measurement) — the first test of the concept's actuation half.
**Status:** `PARTIALLY PRE-EMPTED` — an architectural enforcement mechanism exists in unreviewed single-author preprints (NRR-Core/NRR-Phi), compared only against an unconstrained baseline. The controlled 3-arm comparison (plain vs instructed vs enforced) isolating the causal contribution of enforcement, on unmodified production models, is unrun. The premise (instructed uncertainty expression misaligns with actual uncertainty) is independently published.
**Confidence it holds:** medium — an architectural enforcer beats an unconstrained baseline in unreviewed preprints, and instruction is independently documented as weak; the causal isolation is missing, not the direction.
**Kill condition:** instructed ≈ enforced on interpretation-set retention — instruction suffices, the enforcement layer is ceremony.
**Scope of the kill:** retires enforcement as a distinct operator and the claim that the runtime can guarantee preservation via this mechanism — nothing broader. Does not touch measurement, revision, lowering, or composition. Not gated on E0.
**Experiment:** [E4](experiments/E4-enforced-ambiguity/)

### H-RELEASE — Revision is an operation, not a request
**Claim:** When evidence contradicts an earlier assumption, programmatically rebuilding the context **without** the assumption (an explicit contraction operation in the sense of AGM belief revision) reduces downstream contamination far more than instructing the model to disregard it.
**Why it matters:** The `release` operator and revision rules earn existence with a quantified effect size; agent pipelines gain a principled alternative to "append a correction and hope."
**Status:** `PARTIALLY PRE-EMPTED` (literature state) — the premise (instructed disregard leaves contamination) is proven independently at least seven times, including at the representation level ("models pretend to forget": the final layer says forgotten while earlier layers still compute from the content). The 3-arm comparison with mechanical rebuild as the third arm and downstream-conclusion contamination as the measured outcome is unrun. Note: a commercial product (XTrace) claims AGM operations at runtime — unverified marketing, no published experiment; "first to apply AGM" is not claimable, "first controlled comparison" is.
**Result:** `REOPENED` (2026-07-19), correcting the `REFUTED` verdict recorded from E5's registered run (2026-07-16). A post-verdict adversarial audit (Mission X) found that the registered B-vs-C contamination separation (B 1/107 = 0.9% vs C 11/107 = 10.3%, Bonferroni-corrected p = 0.0089) **does not exist under a valid instrument** — the bidirectional NLI contamination metric fires on the requirement scaffold shared between a stale sentence and its corrected replacement, not on any real assertion of the stale conclusion. Under a claim-grounded replacement instrument (instrument-v2), all three E5 arms carry ~0 real contamination: Arm-C 0/11 real echo, Arm-B 0/1, with the *same* flagged item (F1-0016/1) appearing in both arms — direct proof the flag tracked sentence template, not arm behavior. The program has no valid measurement of an operator-induced revision failure; the only such measurement it had was this artifact. A correction note is drafted for owner review and publication: [CORRECTION-NOTE-DRAFT.md](experiments/E8-instruction-breakpoint/coldstart-package/x1-anatomy/CORRECTION-NOTE-DRAFT.md); standalone statement of the methodological finding: [FINDING-NLI-ARTIFACT.md](experiments/E8-instruction-breakpoint/coldstart-package/mission-x/FINDING-NLI-ARTIFACT.md). A distinct, real, disclosed defect (not contamination): DANGLING_RULE — 2/11 Arm-C items where contraction computes the corrected value and retains the governing rule but never draws the final Boolean (under-completion), fix specced and gated to any future operator retest. Results record: [results/E5-reclosure/2026-07-15-registered-run/](results/E5-reclosure/2026-07-15-registered-run/) (frozen artifacts unchanged — this is a re-interpretation of the same banked data, not a re-run). H-BREAKPOINT, derived from the original refutation, itself ran to verdict independently of this correction (E8: Block B, no axis broke) — see [below](#h-breakpoint--instructed-revision-degrades-along-measurable-difficulty-axes).
**Confidence it holds:** medium — the premise (instruction leaves contamination) is still replicated at least seven times in the literature, but this program's own controlled three-arm isolation, having been withdrawn as an instrument artifact, no longer provides supporting evidence either way. The question is open again, not settled in either direction.
**Kill condition:** instructed-disregard ≈ mechanical rebuild on downstream contamination, measured on a claim-grounded (not sentence-shape) instrument. Not yet validly tested — the one run that attempted this measurement is withdrawn.
**Scope of the kill:** would retire `release` as currently formulated and localized disciplined revision via this mechanism — nothing broader. Does not touch grounding or the other controls. Not gated on E0.
**Experiment:** [E5](experiments/E5-reclosure/)

### H-BREAKPOINT — Instructed revision degrades along measurable difficulty axes
**Claim:** There exists a task-difficulty regime in which instructing a model to retract an assumption and revise everything that depended on it measurably degrades — the instruction baseline (E5's Arm B) has a failure regime reachable by scaling difficulty along pre-chosen axes.
**Why it matters:** Derived from E5's original registered result (2026-07-16, since withdrawn as an instrument artifact — see H-RELEASE above). Every remaining operator experiment silently assumes instructed revision fails somewhere; H-BREAKPOINT tests that premise directly instead of assuming it, as a dose-response study on the instruction baseline alone, with **no operators anywhere**.
**Status:** `RAN TO VERDICT` (2026-07-19) — Phase 0 froze 2026-07-17 (Zenodo DOI [10.5281/zenodo.21404864](https://doi.org/10.5281/zenodo.21404864)); the registered dose-response run executed and reached the program's Block-B verdict. The registered depth axis (A1) was found invalid as built (an undisclosed polarity inversion made it measure revision success, not contamination); rebuilt and re-scored — see [A1V2-DEPTH-REBUILD.md](experiments/E8-instruction-breakpoint/A1V2-DEPTH-REBUILD.md). The program verdict itself rests on A3 (correctly polarized) and the fixed A2, and is unaffected by the A1 defect.
**Confidence it holds:** low — **kill condition fired.** No axis broke at practical scale on any correctly-instrumented, correctly-polarized axis tested (A2, A3, and the rebuilt A1/X4, true floor 0/447).
**Kill condition:** = E8 outcome (b). No frozen axis produces a monotone dose-response across ≥ 3 dose levels that crosses the pre-registered absolute contamination threshold at its top level, at practical scale. A single-dose bump not extending to a monotone curve is not a break. **Fired** — Block B, axes_broke = [].
**Consequence edges (lattice):** outcome (b) fired — a **program-level conclusion condition**: instructed revision holds everywhere validly tested at practical scale, closure-as-a-runtime-tool is unnecessary for revision on tested corpora, and this is recorded as the program's publishable negative for the revision-difficulty line. This does **not** auto-confirm H-ENFORCE or any reformulated H-RELEASE — an operator must still beat instruction under its own separate test — and it does not touch the measurement hypotheses (H-SCALAR, H-PC, H-INV, H-VOL) or the abstraction hypotheses (H-LOWER, H-COMPOSE). The compaction operator (a distinct mechanism from instruction difficulty) is tested separately by [H-COMPACT](#h-compact-exploratory--iterated-compaction-accumulates-revision-contamination) below, and remains the operator line's one open regime.
**Experiment:** [E8](experiments/E8-instruction-breakpoint/)

### H-COMPACT (exploratory) — Iterated compaction accumulates revision contamination
**Claim:** An iterated summarize-and-continue operator, applied to a live reasoning context across correction turns, accumulates revision contamination beyond a matched no-compaction instruction baseline, rising monotonically with cycle count.
**Why it matters:** Descends from the operator-line question left open by H-BREAKPOINT and the (since-withdrawn) H-RELEASE result. A compaction cycle is a *mechanical contraction applied to a live context* — an operator, not a difficulty axis — so it was dropped from E8 (registered operator-free) and given its own exploratory experiment, E9.
**Status:** `EXPLORATORY, RAN, RE-SCOPED` (2026-07-19) — not a registered entry with OSF-style pre-registration; instrument, corpus, and pins were frozen and disclosed before the run. Kill condition (b) fired on the data as scored (0/1800 real contamination at every arm/dose), but a post-verdict adversarial re-check found the summarizer never reached its registered 30–50% compression band (achieved median ratio 0.94; 0.5% of rows in-band; the band-exclusion guard was inert and did not catch it). The verdict is therefore re-scoped, not settled: near-lossless summarization leg survived (corrections held under repeated near-lossless compaction); the real-compression leg is untested, not refuted.
**Confidence it holds:** low — the one leg actually tested (near-lossless) showed no contamination, but that leg is the operating point the design explicitly warned against as a "strawman" that would trivially pass (DESIGN.md §10); the leg that would be a genuine test (real 30–50% compression) has not run.
**Kill condition:** compaction contamination does not rise monotonically across cycle levels and does not cross θ=5% at the top level. Fired on the near-lossless data as scored; not yet meaningfully tested at the registered compression band.
**Scope of the kill:** would close the compaction line with a bounded negative at the tested operating point only — nothing broader, and explicitly not at the registered band until the band-enforcement fix lands and the experiment re-runs.
**Experiment:** [E9](experiments/E9-compaction-cycles/)

### H-LOWER — Structural specs are a real abstraction (lowering invariance)
**Claim:** The same structural specification ("claims grounded in sources", "conclusions rigid under paraphrase") lowered onto two **independent** enforcement backends — post-hoc verification and decode-time enforcement — produces agreeing verdicts. Implementation-independent semantics is what makes a specification layer an intermediate representation rather than a collection of tools.
**Why it matters:** This is the falsifiable form of the entire "compiler for AI computation" idea. SQL became an abstraction because the same query means the same thing on every engine. Note: lowering invariance is a structural-coherence test; it requires no shared latent factor among G/R/P, and is not gated on E0/H-SCALAR.
**Status:** `OPEN` — the claim has never been stated in the literature. Both backend types exist separately; the one system that compiles one constraint model to two layers runs them sequentially (generate-then-validate) and never compares verdicts.
**Confidence it holds:** low — never tested by anyone; both backends exist separately and nothing is known about their agreement. Genuine white space cuts both ways.
**Kill condition:** verdict agreement < 70% across lowerings, or disagreements unsystematic (pre-registered bands: ≥ 85% agreement with κ ≥ 0.7 confirms). (A *systematic* disagreement taxonomy would be a publishable finding in its own right: a map of where "the same property" means different things at different enforcement points.)
**Scope of the kill:** retires the architecture-independent Closure IR and portable specifications across backends (the LLVM-like part of the vision) — a vendor- or model-specific Closure DSL could still survive. Downstream: undermines any control-plane design that specifically requires backend portability (an explicit dependency, not a direct kill). Does not touch the operators, composition, or the measurements.
**Experiment:** [E6](experiments/E6-lowering-invariance/) — with an expressiveness A/B (E6b) gated on E6 passing; the aggregate-score portion of that A/B additionally assumes H-SCALAR. E6/H-LOWER itself is not gated on E0.

### H-COMPOSE — Composed checks catch what isolated checks miss
**Claim:** Pipelines composing the tests (grounding feeding ambiguity-checking feeding collapse-detection) catch real failures that no individual test catches.
**Why it matters:** Decides "system" vs "library" for the measurement layer.
**Status:** `OPEN` — designed in the program's prior corpus (30–60 tasks, three adversarial task types), unrun. Whether the tests aggregate to one score (H-SCALAR) and whether *composing* them adds detection power are separate questions; this hypothesis does not require a positive E0.
**Confidence it holds:** low — the program's own earlier adversarial review left this contested; designed to be settled, not assumed.
**Kill condition:** fewer than 5 composition-only catches across the battery, or catches not confirmed by human review.
**Scope of the kill:** retires the compositional algebra at that level and the claim that combining operators adds detection/control power — independent instruments remain useful. Not gated on E0.
**Experiment:** [E7](experiments/E7-composition/)

---

## Later architectural hypotheses

These depend on the results above and require their own future experiments. They are **not** established by E0–E7 alone, and are recorded here so the architecture's epistemic status is explicit rather than implied.

### H-CONTROL-PLANE — a compiler and runtime can realize structural specs
**Claim:** A compiler and runtime can realize a structural specification by selecting and composing model-control mechanisms (prompting, retrieval, constrained decoding, steering, verifier passes, adapters, tuning) — exposing them as composable backends for a higher-level specification rather than as unrelated application-level abstractions.
**Status:** `OPEN`. **Confidence:** very low. Not established by E0–E7; depends on H-ENFORCE, H-RELEASE, H-COMPOSE, and H-LOWER, and needs its own experiments.
**Itself a lattice, not a monolith:** an execution control plane is several separable properties — compiling a specification, selecting mechanisms, composing mechanisms, verifying contract satisfaction, optimizing cost and latency, recovering from failure, moving across backends. These may not succeed or fail together. When their experiments are designed, the governing rule applies again: each property gets its own scoped hypothesis and kill condition — never one all-or-nothing control-plane test.
**Kill condition:** to be pre-registered when those experiments are designed.
**Experiment:** future.

### H-NATIVE — closure operations can manipulate model-native computation
**Claim:** Closure operations can eventually manipulate model-native computation and be transferred between models without linguistic reconstruction — structural rather than prose-based model communication.
**Status:** `OPEN`. **Confidence:** very low. Requires evidence not provided by E0–E7; a long-term research hypothesis with no current experiment and no feasibility claim.
**Kill condition:** to be pre-registered if and when it is made testable.
**Experiment:** future.

---

## Consequence matrix

The program has no single alive/dead verdict. Each experiment directly retires only the claim it measures; broader claims survive, weaken, or die by their explicit dependencies. What survives each result — stated in advance:

| Result | What becomes justified / what survives |
|---|---|
| E0 (H-SCALAR) confirms | an aggregate closure score is justified |
| E0 refutes | scalar aggregation retired; the independent structural hypotheses remain logically open; closure, if it survives, is represented as a multidimensional profile, not one number |
| E4 / E5 (H-ENFORCE / H-RELEASE) confirm | those closure operations have causal reality |
| E4 / E5 refute | retire or reformulate those operators only; measurements and other controls remain |
| E5 (H-RELEASE) **REOPENED 2026-07-19** — the 2026-07-16 registered refutation is withdrawn as an NLI instrument artifact; correction note drafted | `release`'s status returns to open; the program has no valid measurement of an operator-induced revision failure; H-BREAKPOINT (derived from the original, since-withdrawn refutation) nonetheless ran and settled independently |
| E7 (H-COMPOSE) confirms | a compositional specification language becomes plausible |
| E7 refutes | retain independent controls; abandon algebraic composition at that level |
| E6 (H-LOWER) confirms | a portable Closure IR becomes plausible |
| E6 refutes | model-specific structural control may remain; the portable IR dies; control-plane designs that require backend portability lose support |
| later optimizer / planning tests confirm | the execution control plane (H-CONTROL-PLANE) becomes plausible |
| native-interface tests confirm | structural model-to-model communication (H-NATIVE) becomes plausible |
| E8 (H-BREAKPOINT) outcome (a) — break found | the difficulty regime where instructed revision degrades re-scopes the remaining operator experiments to it — does **not** auto-confirm any operator |
| E8 (H-BREAKPOINT) **outcome (b) fired — no break, 2026-07-19** | instructed revision holds everywhere validly tested at practical scale; closure-as-a-runtime-tool is unnecessary for revision on tested corpora — program-level negative of record. Depth axis (A1) required a post-verdict rebuild (polarity inversion); program verdict itself rests on A3+A2 and is unaffected |
| E9 (H-COMPACT, exploratory) near-lossless leg | corrections survive repeated near-lossless summarization (0/1800 real); real-compression leg untested, re-run open |

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
