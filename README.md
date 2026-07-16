# Closure

A research program on model-native inference structure in large language models: a testable mechanistic hypothesis for hallucination and confidence, causal (non-LLM-judged) verification of model outputs, and whether a multidimensional structural specification can become a portable control layer for learned computation.

Originated and led by [Vlad Ryzhkov](AUTHORS.md). Public since 2026-07-14; execution has begun. Two verdicts are on record: E3 (future-output volume) `confirmed-shaped` at exploratory grade, and E5 (mechanical reclosure) **REFUTED** at registered grade — the program's own flagship revision operator lost to a one-paragraph instruction, published in stronger-than-registered form and archived under DOI [10.5281/zenodo.21399411](https://doi.org/10.5281/zenodo.21399411). The remaining experiments are pre-execution, and that is still the point: the plan is public so it can be attacked before execution hardens its assumptions ([STATUS.md](STATUS.md), [LOG.md](LOG.md)).

## Choose your entry point

- **You do interpretability or evaluation research** → the [central question](#the-hypothesis), then [E0](experiments/E0-closure-existence/) and the [kill conditions](HYPOTHESES.md). The invitation is not agreement — it is the strongest valid objection, the smallest decisive experiment, or the cleanest way to retire an unnecessary concept ([OBJECTIONS.md](OBJECTIONS.md)).
- **You want to build or contribute** → [STATUS.md](STATUS.md) for what is implementable now (the shared G/R/P instrument, useful regardless of whether the theory holds), then [CONTRIBUTING.md](CONTRIBUTING.md).
- **You came for the founding theory** → [CONCEPT.md](CONCEPT.md), the full vision stated before any of it is proven, and [the reduction history](background/reduction-history.md) — how it was compressed under adversarial review, what that got right, and what it dropped without disproving.
- **You are evaluating the work or its author** → the [reduction history](background/reduction-history.md) and [HYPOTHESES.md](HYPOTHESES.md) show how a new problem was formed, reduced, and made falsifiable; [AUTHORS.md](AUTHORS.md) states authorship and how contribution is credited.

## Problem

Production evaluation of LLM outputs is LLM-as-judge — a model grading a model, inheriting its failure modes. The causal alternatives are published and validated (leave-one-out attribution, perturbation testing, semantic clustering) but ship nowhere together, and nobody has asked whether the properties they measure are related. Meanwhile the 2025–26 literature on hidden-state dynamics contradicts itself: hallucination is reported both as a trajectory settling *too early* into a stable-but-wrong attractor (arXiv:2604.15400) and as *failing to settle* (arXiv:2602.09825, 2507.06722) — and no study measures the variable that could reconcile them: whether the state settled **before or after incorporating the provided evidence**.

## The measurement, on one example

*The numbers below are illustrative — a worked example, not a measurement. Recorded runs and verdicts live in [`/results`](results/).*

A RAG model is asked *"What did the 2023 audit find regarding vendor payments?"*, with the audit report as source **[A]**. It answers:

> 1. The audit identified $2.1M in duplicate vendor payments **[A]**.
> 2. Duplicate payments of this kind typically indicate missing three-way-match controls **[A]**.

The citations are typographically identical. An LLM judge grades both "supported" — both are *consistent* with the source. Consistency cannot distinguish **derived from** and **merely compatible with**.

Intervene instead: remove [A], regenerate three times, compare claims by NLI entailment. Claim 1 disappears — grounding score **G ≈ 0.9**, causally grounded. Claim 2 persists verbatim — **G ≈ 0.1**: the source is not why the model said it (decorative citation or trained-in knowledge; the test reports that ambiguity rather than hiding it).

The same intervention logic gives **R**, rigidity (rephrase the input five ways: which conclusions survive?) and **P**, ambiguity preservation (generate ten times: how many semantically distinct answers does the model hold?). Every test replaces an opinion with an intervention.

RAG is the teaching case, not the scope. The identical intervention runs wherever a model was given inputs and produced an output: remove the requirement from the spec — does the generated code change, or was it going to write that anyway? Remove the tool result from the agent's context — does its action change, or was the lookup decorative? Remove the lab values — does the clinical suggestion change? **Given-inputs → output is the unit of verification; the domain is irrelevant.**

## The hypothesis

Define **closure**: the terminal state of inference-time reorganization — the structures determining the output have stopped changing and are mutually consistent with the given constraints. This is a multidimensional, typed object (the founding specification is a tuple `C = (B, I, P, F, G, U, R, O)`, not a single number), and the program tests its properties separately rather than through one master gate.

The first of those tests asks the narrowest version of the question. **[H-SCALAR](HYPOTHESES.md#h-scalar--grounding-rigidity-and-ambiguity-preservation-share-one-latent-factor):** grounding, rigidity and ambiguity preservation are readouts of one *scalar* factor — testable by factor analysis over score matrices (the instrument reported as validated on capability benchmarks in arXiv:2507.20208 — abstract-checked, not yet human-verified, per [VERIFICATION.md](VERIFICATION.md); never applied to these axes). Pre-registered: a single factor explaining ≥ 60% of shared variance with same-sign loadings, surviving difficulty controls, confirms; pairwise |r| < 0.2 refutes.

That test is [E0](experiments/E0-closure-existence/) — cheap, decisive, and precisely scoped. It decides whether the tests can be *aggregated into one closure score*; it does **not** gate the architecture. A negative E0 retires the single score and requires closure to be represented as a multidimensional profile — it leaves the operator, composition, and lowering hypotheses ([E4](experiments/E4-enforced-ambiguity/)–[E7](experiments/E7-composition/)) logically untouched, because factor analysis has no power over whether a structured specification exists. Under the program's governing rule — *each experiment may directly retire only the claim it measures* — the claims form a lattice, and what survives each result is read off the [consequence matrix](HYPOTHESES.md#consequence-matrix).

## The architectural thesis (long-term, conditional)

The experiments are the repository's immediate scientific center. But they are chosen because the founding concept already proposes an architecture, and each experiment tests a prerequisite of it. Stated plainly so its epistemic status is unmistakable — this is the long-term hypothesis, not a current result:

```text
Human intent
        ↓  intent compiler
Structural specification          ← a multidimensional typed contract, C = (B,I,P,F,G,U,R,O)
        ↓  model-specific lowering
Available control mechanisms      ← prompting, retrieval, memory, tool use, verifier passes,
        ↓                            constrained decoding, steering, adapters, tuning
Model execution
        ↓  structural inspection
Observable
```

If the load-bearing hypotheses survive, this could develop into a **model-independent execution-control layer for learned computation.** Under such a layer, the mechanisms above would no longer be exposed as unrelated application-level abstractions; they would become alternative or composable *backends* used to realize one higher-level structural specification — the relationship a compiler has to instruction sets, not the relationship a set of libraries has to each other. This is a possibility conditional on results, stated as a direction; it is not claimed to exist.

Three stages, kept explicitly distinct:

**1 — What exists in the repository now.** The ontology ([CONCEPT.md](CONCEPT.md)); a working operator vocabulary (constrain, release, couple, decouple, perturb, stabilize); the structural-specification proposal; the hypotheses with their kill conditions ([HYPOTHESES.md](HYPOTHESES.md)); the nine experiment protocols; the operational definitions of the settling quantities ([background/formal-core.md](background/formal-core.md)); and the four measurement methods (G, R, P, F) that are implementable today against any model API.

**2 — What the current experiments test.** Whether the closure dimensions aggregate to one scalar score (E0); whether individual operations such as enforcement (E4) and release (E5) have causal value over instruction; whether one specification retains its semantics across independent lowerings (E6); and whether composed structural checks add detection power (E7). These are prerequisites of the architecture, tested one property at a time.

**3 — What may become possible later (not implemented, not established).** A compiler targeting multiple model-control mechanisms; an optimizer that selects or composes implementation strategies by cost and quality; a runtime that realizes and verifies computational contracts and recovers from failure; persistent learning of desired closure transitions; and structural rather than prose-based model-to-model communication. These are the later architectural hypotheses ([H-CONTROL-PLANE, H-NATIVE](HYPOTHESES.md#later-architectural-hypotheses)); they are **not** established by E0–E7 and require their own future experiments — and, like the control plane itself, they will be governed as a lattice of separable claims, never one all-or-nothing test.

One scope limit, stated directly to avoid overreach: **E6 does not validate the compiler, the optimizer, or the execution-control plane.** It tests only the narrower prerequisite — that a structural specification can retain its semantics across two independent enforcement backends. A positive E6 makes a portable intermediate representation *plausible*; it does not build the toolchain above it.

## The experiments

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/claim-structure-dark.svg">
  <img alt="The claim structure of the program: closure as a hypothesized multidimensional property of every AI answer; E0 tests whether its measured dimensions aggregate to one scalar score; four directions — mechanism (E1), physics (E2), operations (E4, E5), abstraction (E6, E7) — each carry their own falsifiable claims, retired only within the property each measures." src="figures/claim-structure-light.svg">
</picture>

Every branch is falsifiable on its own, and each is retired only within the property it measures — no experiment kills a claim broader than what it tests. E0 decides the narrowest version (do the dimensions aggregate to one score), not whether the whole architecture stands. Full protocols with pre-registered verdict conditions in [`/experiments`](experiments/) — along with the build-dependency graph for contributors. No timelines; ordering is dependency and cost only.

| ID | Claim under test | Literature state |
|---|---|---|
| [E0](experiments/E0-closure-existence/) | G/R/P aggregate to one scalar factor (not whether a structured spec exists) | Instrument reported validated (abstract-checked); this application unrun; nearest candidate withdrawn by its authors |
| [E1](experiments/E1-premature-closure/) | Hallucination = settling before evidence incorporation | Direction contested across published papers; the coupling unmeasured |
| [E2](experiments/E2-conserved-quantities/) | The forward pass has conservation laws; violations predict failure | No prior work on either half |
| [E3](experiments/E3-future-volume/) | Future-output diversity is continuous and linearly decodable pre-sampling | Binarized probe exists; continuous target, confidence baseline, belief-state link do not |
| [E4](experiments/E4-enforced-ambiguity/) | Enforced interpretation coverage beats instruction | Enforcement exists (unreviewed, 2-arm); causal isolation unrun |
| [E5](experiments/E5-reclosure/) | Mechanical context rebuild beats instructed disregard | REFUTED by registered run 2026-07-16 (contraction worse than instruction); [results record](results/E5-reclosure/2026-07-15-registered-run/) |
| [E6](experiments/E6-lowering-invariance/) | Independent enforcement backends agree on one spec's verdicts | Claim never stated in the literature |
| [E7](experiments/E7-composition/) | Composed checks catch what single checks miss | Designed; unrun |
| [E8](experiments/E8-instruction-breakpoint/) | Instructed revision degrades along measurable difficulty axes (no operators) | Derived post-E5; registered before design freeze |

## What each result changes

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/deliverables-dark.svg">
  <img alt="The business consequence chain. The bottleneck: work cannot be delegated to a model whose only scalable checker is another model — human review does not scale, LLM-as-judge is circular trust, regulators require evidence, not opinion. The program completed makes verification independent of the verified: causal tests, measured dynamics, enforced specifications. Four consequences: incidents intercepted pre-output (requires E1); risk-tiered automation routed by measured reliability (requires E0, E2, E3); governable agent pipelines with revision and enforcement as auditable operations (requires E4, E5); portable compliance — one verification spec enforced identically on any model, vendor or backend (requires E6). End state: delegation at production scale — model output converted from a liability you review into a governed input you delegate to." src="figures/deliverables-light.svg">
</picture>

The verification instrument itself is unconditional — it is built to run the experiments and stands regardless of their outcomes. Where it lands is every setting with the given-inputs → output shape:

| Domain | Given → produced | The question answered by intervention, not opinion |
|---|---|---|
| Code generation | spec + codebase → change | Did the change derive from the requirement — or would the model have written it anyway? |
| Autonomous agents | tool results + constraints → actions | Did the action depend on what the tool returned? Can a retracted assumption actually be retracted? |
| Medical | patient data + history → assessment | Is the conclusion grounded in *this* patient's values, not the textbook prior? |
| Legal | case law + statutes → analysis | Is the cited precedent load-bearing or decorative? |
| Finance & compliance | filings + rules → report | Does every claim carry causal, auditable evidence a reviewer can inspect? |
| Research / RAG | sources + question → cited answer | Which citations are causal and which are decorative? |
| Content | brand guidelines + brief → copy | Did it follow the brief, or generate the generic default? |

Demand concentrates first where verification is becoming mandatory (EU AI Act high-risk systems, FDA-regulated AI/ML devices) and where unverified output already carries legal cost — but the instrument is domain-blind by construction: the model is a callable, the inputs are whatever you gave it.

Each consequence in the figure above is bought by the named confirmations; refutations close questions the field currently keeps reopening. In detail:

| | Confirmed | Refuted |
|---|---|---|
| **E0** | An aggregate closure score is justified | Scalar aggregation retired; closure reported as a multidimensional profile; the structural claims (E4–E7) and the tests stay valid |
| **E1** | Hallucination is a measurable event with a mechanism — intervene before readout, not after the text | The late-instability account wins; the field's contradiction resolves either way |
| **E2** | The first conservation law of transformer inference | "Native invariants" demoted to metaphor, on the record |
| **E5** | A principled revision operation with quantified effect; context management stops being folklore | Instruction suffices — surprising against seven published failures, publishable as such |
| **E6** | A portable structural IR becomes plausible; a compiler-style prototype is worth building | No portable IR — the idea dies cheaply, before anyone builds the expensive version |

E3, E4 and E7 carry the same two-sided structure in their protocols. A program whose total-refutation branch still produces value is not a bet on being right; it is a bet on the questions being worth deciding.

## Retired claims, citation status

Claims that failed adversarial review are recorded and closed — "new computational paradigm," "complete operator algebra," "convergent design," closure-as-formalized-mathematics ([HYPOTHESES.md § Retired](HYPOTHESES.md#retired-claims)). Two founding ideas were independently published by others in 2026; priority cannot be publicly established, so they are recorded as convergence, not prediction ([reduction history](background/reduction-history.md)). Every citation carries an explicit verification status, most currently unverified pending a human read of the primary source ([VERIFICATION.md](VERIFICATION.md)) — flipping one row is the smallest complete contribution.

## Documents

- [STATUS.md](STATUS.md) — the present stage stated plainly: what is published, ready, not yet run, and explicitly not claimed
- [AUTHORS.md](AUTHORS.md) — origination, leadership, and how contribution is credited
- [OBJECTIONS.md](OBJECTIONS.md) — the strongest objections to the program, each classified and answered
- [CONCEPT.md](CONCEPT.md) — the founding vision, preserved as hypothesis
- [background/formal-core.md](background/formal-core.md) — the operational definitions: settling depth, incorporation, premature closure, the bridge claim, future volume, conserved quantities; what remains unformalized, named as open problems
- [HYPOTHESES.md](HYPOTHESES.md) — every claim with its kill condition; retired claims with cause of death
- [METHODOLOGY.md](METHODOLOGY.md) — every method anchored to its named standard, declared as a contribution, or listed as a known nonconformance with its fix
- [decisions/](decisions/) — the methodology choices each experiment's protocol leaves open, frozen with their reasoning (proposed until pre-registered)
- [experiments/E0-closure-existence/PLAN.md](experiments/E0-closure-existence/PLAN.md) — how the shared G/R/P instrument is built and run to a first verdict
- [background/](background/) — prior-art map, closure vs Design-by-Contract, reduction history, how the execution plan was derived
- [CONTRIBUTING.md](CONTRIBUTING.md) — evidence standards, how to run or attack an experiment

MIT license.
