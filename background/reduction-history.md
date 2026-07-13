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
