# Reduction History

The program's own origin is a documented case study in how new concepts get mis-scored when evaluated by comparison against existing knowledge. It is kept public because the failure mode it exhibits is general, and because two of its artifacts (a substituted confirmation and an independent convergence) are part of the evidence record.

## What happened

1. **A full concept was written** ([CONCEPT.md](../CONCEPT.md)): an ontological account of transformer computation, a definition of closure, a specification layer with six operators, and a set of engineering consequences (mechanical hallucination definition, geometric confidence, revision-as-operation).
2. **The concept was adversarially reduced.** Multiple rounds of research, an adversarial claims audit, and engineering review compared each claim against existing literature. Claims that matched existing work were marked "known"; claims without existing evidence were marked "unverified." The surviving product was the measurement layer alone — four verification tests — with the vision layers set aside.
3. **The reduction was itself audited.** A later verification effort compared the original and reduced versions element by element against the live literature, with a different question: not "which claims match known work?" but "which claims are *residuals* — not expressible in the existing basis — and what would test them?"

## What the audit found

**The reduction kept every operator that reads and dropped every operator that writes.** The original design was a closed control loop: measure structural properties (perturb, couple, preserve-check, forbid-check) *and act on them* (constrain, release, decouple, stabilize). The reduced product was the sensor array with the actuators removed. None of the reduction's evaluations had tested the actuation half — it was dropped without being disproven. Experiments [E4](../experiments/E4-enforced-ambiguity/) and [E5](../experiments/E5-reclosure/) test it.

**One "confirmation" was a substitution.** The original hypothesis "native invariants exist" referred to quantities conserved *along a single forward evolution*. The reduction marked it confirmed by citing cross-*model* representational universality — invariance across systems, a different mathematical object than conservation along a trajectory. The hypothesis in its original form had never been tested. [E2](../experiments/E2-conserved-quantities/) tests it.

**One kill was a type error.** "Closure" was killed as "Design by Contract, 40 years old" — a projection onto the nearest neighbor in product space, when the concept's actual lineage is the equilibrium tradition (DEQ, Hopfield, energy-based models). The argument is made precisely in [closure-vs-dbc.md](closure-vs-dbc.md); the empirical question it raises is [E0](../experiments/E0-closure-existence/).

**Two ideas independently converged with later publications.** The founding concept contained (a) hallucination as settling into a stable-but-wrong configuration and (b) reasoning as progressive contraction of the reachable-future space, with the contraction pattern carrying reliability information. Both appeared as independent publications in 2026 (attractor-commitment and hallucination-basin papers; entropy-trajectory-shape and stepwise-informativeness papers). The concept was developed without knowledge of these works, and they without knowledge of it; since public priority cannot be established from private records, this is recorded as **independent convergence**, with no priority claimed. The ideas are now prior art; the program targets the open edges past them (E1, E3).

## The general lesson

Evaluating a new concept by projecting it onto existing knowledge is asymmetric: it reliably detects overlap and reliably *cannot* detect residual. "Unverified" under such an evaluation conflates two different states — *tested and failed* and *not expressible in the comparison basis* — and treating the second as the first silently deletes exactly the content that made the concept new. The audit's correction was procedural, not rhetorical: for every claim, state the nearest neighbor, state the residual, and if the residual is contentful, produce the experiment and its refutation condition. That procedure's output is this repository.

The reduction was not wasted work. It killed four claims that deserved to die ([HYPOTHESES.md § Retired](../HYPOTHESES.md#retired-claims)), corrected costs and overclaims, and produced the measurement tooling that five of the eight experiments now depend on. The failure was not rigor — it was applying only one direction of rigor.

## A governance correction, made before any experiment ran

The first published governance declared E0 a gate over the whole program: a negative E0 would retire the term "closure" and pull the floor out from under the specification layer. A pre-execution audit found this rested on two nested category errors, and both are kept visible here because the kill conditions themselves being open to criticism is part of the program's honesty.

The first error: "one coherent object to specify over" was conflated with "one scalar latent factor." E0's instrument is factor analysis, which can decide only whether G, R and P covary onto a single dimension. But the founding specification is already a multidimensional typed object, `C = (B, I, P, F, G, U, R, O)`; a specification's coherence rests on stable semantics, composition, and portability, not on statistical covariance (SQL, a type system, and a deployment manifest are all coherent without a single latent "quality" factor). So E0 has the power to retire the single closure *score* — not the structural contract, the operators, the composition layer, or the intermediate representation, which are tested separately (E4–E7) and whose kill conditions never mention a shared factor.

The second error appeared in the first attempt to fix the first: it replaced the scalar gate with one large "structural" hypothesis, killed only if E4 *and* E5 *and* E6 *and* E7 all failed. That conjunction is survivable, not sharp — complete failure of lowering and composition would leave the architecture "alive" if any single operator worked. It repeated the original mistake one level up: collapsing many distinct architectural claims into one master claim, exactly the premature collapse the ontology warns against.

The correction is a claim lattice under a single governing rule: *each experiment may directly retire only the claim it measures; broader architectural claims survive, weaken, or die by their explicitly documented dependencies and their own tests.* Each property — scalar aggregation, enforcement, release, composition, lowering — is its own hypothesis with its own scoped kill condition, and architecture-level viability is read off a [consequence matrix](../HYPOTHESES.md#consequence-matrix) rather than decided by any single verdict. The execution control plane and native model-to-model communication are recorded as later hypotheses requiring their own future tests, not as claims E0–E7 could establish.

The correction was made before any experiment ran — a repair of an overbroad precommitment, not a change made after seeing a result. Its deeper point is that the governance now instantiates the ontology it studies: preserve distinctions, couple each claim to its evidence, release only what evidence invalidates, and do not collapse structures that have not been tested together.

## A design repair to E5, made before any run

A pre-execution audit of E5's protocol found two defects; both were repaired before any pilot, corpus, or registration existed.

The first was a selection-on-outcome loop. The contamination detector drove Arm C's contraction (choosing which claims to delete) and also scored the experiment's outcome (how much contamination remains). An intervention that deletes whatever the outcome instrument flags wins on that instrument partly by construction. The repair separates the roles: the detector remains Arm C's contraction rule, and the outcome is referenced to per-task ground-truth annotations — which conclusions must change under ¬A and which must persist — that the contraction rule never touches ([0007](../decisions/0007-e5-reclosure.md)).

The second was a missing outcome dimension. With contamination as the only measure, an arm can win by deletion: remove enough content and nothing depends on anything. The repair adds completeness — retention of must-persist conclusions — as a co-primary outcome with a pre-registered non-inferiority margin. A contamination win with completeness inferior beyond the margin is pre-registered as *contraction wins by deletion*, a failure of the operator as formulated, not a confirmation.

Like the governance correction above, this is a repair made before data existed, kept visible because outcome definitions being open to criticism is part of the program's honesty.
