# E6 — Lowering invariance

**Question:** Does a structural specification have implementation-independent semantics — do **independent** enforcement backends, given the same spec, agree on verdicts?

**Hypothesis:** [H-LOWER](../../HYPOTHESES.md#h-lower--structural-specs-are-a-real-abstraction-lowering-invariance). This is the falsifiable form of the claim that structural specs constitute an intermediate representation. SQL became an abstraction because the same query means the same thing on every engine; if verdicts here depend on the enforcement mechanism, there is no abstraction — only tools.

**E6 does not depend on E0.** Lowering invariance is a structural-coherence test; it requires no shared latent factor among G/R/P. A failure retires the architecture-independent (portable) Closure IR — a model-specific structural DSL could still survive — and, by explicit dependency, undermines any control-plane design that requires backend portability. It does not touch the operators or the measurements.

## Status and prior art

`OPEN` — the claim is absent from the literature (verified by direct search; no paper states it, no experiment measures it). The components exist separately:

- **Decode-time semantic enforcement:** SEM-CTRL (arXiv:2503.01804 — MCTS decoding under answer-set-grammar constraints), Token-Guard (arXiv:2601.21969, ICLR 2026 — per-token self-checking with pruning/regeneration), sequential Monte Carlo steering (arXiv:2306.03081, 2504.13139). All single-backend systems.
- **Post-hoc semantic verification:** MiniCheck-class entailment verifiers, NLI grounding checks, leave-one-out attribution. All single-backend.
- **Nearest miss:** ATLAS (arXiv:2510.25890) compiles one constraint model to a generation-time layer and a validation layer — but runs them **sequentially** (generate under constraints, then validate and repair) for schema/engineering-artifact validity. Composition, not comparison; syntax, not semantics.
- DSPy compiles prompts, demonstrations and weights against metrics — not enforcement backends (checked against 3.x). Practitioner discourse compares constrained decoding vs post-hoc retry for JSON/regex conformance as a cost/reliability tradeoff; agreement has never been measured even for syntax.

Citation statuses: [VERIFICATION.md](../../VERIFICATION.md).

## Protocol

1. **Fix one spec.** Concretely: `every claim causally grounded in a provided source` + `key conclusions rigid under paraphrase at threshold τ`.
2. **Lowering 1 — post-hoc.** The measurement tooling: leave-one-out grounding + paraphrase battery, run after generation, verdict per output.
3. **Lowering 2 — decode-time.** The same properties enforced during generation on an open-weights model (verifier-in-the-loop / logits-processor machinery in the Token-Guard/SMC family), issuing its own verdict.
4. **Independence discipline.** The two lowerings run **separately** on the same task corpus — never as a pipeline (that is ATLAS's shape and tests nothing about invariance). Neither sees the other's verdicts.
5. **Measure.** Verdict agreement rate; and for every disagreement, a classified cause (sampling variance, threshold semantics, enforcement side-effects on the text itself, genuine semantic divergence of "the same property" at different enforcement points).

## Verdict conditions (pre-registered)

- **CONFIRMED** iff verdict agreement **≥ 85%** (Cohen's κ ≥ 0.7) AND every disagreement classifies as variance or threshold noise rather than semantic divergence — the spec means the same thing under both lowerings; the IR claim stands.
- **REFUTED** iff agreement **< 70%** or disagreements are unsystematic — the compiler framing dies, and the registry records it.
- Between the bands: the disagreement taxonomy is the result.
- **Middle outcome, publishable either way:** a *systematic* disagreement taxonomy — a map of where "grounded" or "rigid" silently changes meaning between checking after and enforcing during. No such map exists for any property.

## E6b — Expressiveness A/B (adoption bet; gated)

A second, explicitly weaker question: does *writing* the spec in a structural language beat expressing the same requirements in a raw prompt, measured by structural-property hit rate on hard tasks? This is not falsifiable in the strong sense — languages are adopted, not proven — so it is reported as an A/B lift only. It runs only if **E6** is positive (the spec has stable semantics across backends); the portion that reports a *single aggregate* structural-quality score additionally assumes a positive E0 (H-SCALAR). E6/H-LOWER itself is not gated on E0.

## Cost and prerequisites

The post-hoc lowering is the measurement tooling. The decode-time lowering is the real engineering lift: open model plus constrained-decoding machinery adapted to semantic properties. Run after the tooling exists.

## Exclusion criteria (pre-registered)

Runs where either lowering crashes are excluded from the agreement statistic but counted and reported separately — a crash is an engineering fact, not a verdict, and folding crashes into disagreements would fake a semantics result.

## Wanted from contributors

- The decode-time enforcement prototype (the program's hardest open engineering problem — and reusable far beyond E6).
- The disagreement-classification rubric, written before any verdicts exist.
