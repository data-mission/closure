# The formal core — operational definitions

**What this document is.** The definitions that make the hidden-state hypotheses exact, assembled into one
object from instruments the experiment protocols already pin separately (E1's settling and incorporation
functionals, E3's volume estimator, E2's nontriviality exclusion). Every definition below is measurable today;
every free parameter is named so a pre-registration can freeze it.

**What this document is not.** A theorem set. The retired claim "closure justified by formal fixed-point
mathematics" ([HYPOTHESES.md § Retired](../HYPOTHESES.md#retired-claims)) stays retired — nothing here proves a
fixed point exists, is unique, or is approached. Section 9 names what remains genuinely unavailable, as open
problems rather than implied capabilities.

## 1. Setting

Fixed model weights θ. A **boundary** `b` is everything the model is given for one generation — prompt,
sources, instructions, tool results ([CONCEPT.md Part III](../CONCEPT.md): "boundary conditions," here a
definition rather than a metaphor). The forward pass produces residual-stream states `h_ℓ`, `ℓ = 0 … L`, with
the residual update `h_{ℓ+1} = h_ℓ + f_{ℓ+1}(h_ℓ; b)`. The evolution is discrete and finite-depth; no
continuum limit and no convergence property is assumed anywhere below.

## 2. D1 — the readout projection

The raw stream does not settle (norms grow; features churn); the closure claim is about the components that
determine the observation. A **readout projection** φ maps a hidden state to the observable's space — in the
pinned instruments, a lens projection to next-token distributions, with the tuned lens primary and the raw
logit lens as robustness check (raw logit lens is known-unfaithful on many models; a plateau can be an
unembedding artifact — [E1](../experiments/E1-premature-closure/README.md), Instruments). φ is an instrument,
not a convenience: every settling claim is φ-relative, φ must be frozen before data, and a registered result
must either replicate across the primary and robustness lens or be scoped to the lens that produced it.

## 3. D2 — settling depth (closure, dynamical sense)

Let `D_ℓ = JSD(φ(h_ℓ), φ(h_{ℓ−1}))` — the per-layer movement of the readout image (E1's settling functional:
`CLSS_ℓ = 1 − D_ℓ`). Given tolerance ε and window w, the **settling depth** is

```
ℓ*(ε, w) = min { ℓ ≤ L − w : D_k < ε  for all  ℓ < k ≤ ℓ + w }
```

— the first layer after which the next w layers act as approximate identity on the readout projection;
**undefined if no such ℓ exists.** The window must be full (`ℓ ≤ L − w`), so a vacuous tail at the last layers
cannot manufacture a plateau — without that bound, ℓ* would trivially exist for every output and "never
settles" would be impossible by definition. This is the operational residue of "fixed point" when the map
changes per layer and depth is finite: not `x* = F(x*)`, but *the readout-relevant components have stopped
changing*. Free parameters `(φ, ε, w)` are instrument choices, frozen at pre-registration.

Two measurable regimes follow, both admissible: a full-window plateau exists (`ℓ*` defined), or none does
(`ℓ*` undefined — "never settles," the late-instability picture). E1's two-regime secondary analysis is
exactly the claim that hallucinations populate both.

**Terminology repair.** "Closure existence" is used in two senses in this program and they are independent:
the *dynamical* sense above (does a pre-readout plateau exist — measured by E1's instruments) and the
*psychometric* sense (do G/R/P sub-indicators share one latent factor — E0's factor analysis). Neither implies
the other. E0's directory name notwithstanding, E0 tests scalar aggregation only; the dynamical existence
question belongs to E1's instrument family.

## 4. D3 — incorporation depth

For a constraint `s ∈ b` (a source, a correction, an instruction), the **incorporation depth** is defined
causally, by the same leave-one-out logic the behavioral G test uses ([README, "The measurement, on one
example"](../README.md)) moved inside the network:

```
τ(s) = min { ℓ : JSD(φ(h_ℓ ; b), φ(h_ℓ ; b∖{s})) > δ }
```

— the earliest layer at which the readout image measurably depends on s. Comparing φ-images (distributions)
rather than raw states is what makes the two runs comparable despite tokenization differences under removal.
δ is frozen with the instrument. If no layer exceeds δ, τ(s) is undefined and s was never incorporated —
the internal analogue of a decorative citation.

The practical single-run estimator E1 pins is ICR (`JSD(Proj, Attn)` — is the layer's update context-driven or
parametric-driven). The relation is stated, not blurred: the causal τ above is the *definition*; ICR is a
frozen *estimator* of incorporation activity. Any registered claim states which of the two it uses.

## 5. D4 — premature closure, and the settling margin

**Premature closure** with respect to constraint s:

```
PC(s)  ≡  ℓ* defined  ∧  ( τ(s) undefined  ∨  ℓ* < τ(s) )
```

— the readout-relevant components stopped changing before the state ever depended on the constraint. An output
that never settles (ℓ* undefined) cannot exhibit premature closure — it belongs to the other regime, and the
two are reported separately, never pooled.
[H-PC](../HYPOTHESES.md#h-pc--hallucination-is-premature-closure) is then: hallucinated outputs exhibit PC at a
rate exceeding faithful outputs — which E1's pre-registered verdict conditions restate with frozen margins
(settling ≥ 3 layers earlier, p < 0.01, incorporation absent before ℓ*).

The **settling margin** is the continuous form:

```
m(s) = ℓ* − τ(s)
```

per (output, source) pair, defined where both ℓ* and τ(s) are. `m > 0`: incorporation preceded settling.
`m ≤ 0`: the premature regime. The two undefined cases are their own reported categories, not points on the
scale: (ℓ* defined, τ undefined) is maximal prematurity — the source never entered at all; (ℓ* undefined) is
the never-settles regime. The margin is what turns E1's binary comparison into a dose-readable quantity.

## 6. D5 — the bridge claim (to be frozen in E1's pre-registration)

The program currently operates two instruments at two levels with no registered relation between them: the
behavioral grounding score G (leave-one-out + NLI, [0002](../decisions/0002-grounding-measurement.md)) and the
hidden-state pair (ℓ*, τ). If both measure the same underlying event — the constraint entering the computation
before it froze — they must co-vary:

> **Bridge claim.** Per (output, source), the behavioral grounding score G(s) is positively associated with
> the settling margin m(s). Effect-size threshold and test to be frozen in E1's pre-registration; the claim's
> direction and its two failure readings are recorded here, in advance.

Both failure directions are informative and neither is absorbed: **no association** means either the behavioral
instrument does not measure settling (G/R/P remain valid causal-verification tooling on their engineering
merits, but lose their theoretical reading as closure measurements), or settling is not the mechanism behind
grounding (the ontology loses its E1 projection even if the depth comparison passes). This is the program's
direct attack on its own known weakest joint — the operationalization distance between manifold-level claims
and text-level measurements. It is deliberately cheap: E1 already labels outputs with the LOO oracle and
already records ℓ* and incorporation timing; the bridge adds a correlation, not an experiment.

## 7. D6 — future volume (E3's object)

For a pre-sampling hidden state h, the **future volume** V(h) is the semantic diversity of the continuation
distribution reachable from h — ground-truth-estimated by sampling N continuations, embedding, and taking the
Gram-determinant semantic volume ([E3](../experiments/E3-future-volume/README.md), protocol step 1).
[H-VOL](../HYPOTHESES.md#h-vol--confidence-is-the-volume-of-reachable-futures-readable-from-the-latent-state):
V is continuous, linearly decodable from h in one forward pass, and informative over verbalized confidence.
The founding claim "reasoning is successive contraction of the reachable-future space" is, in this notation,
V decreasing along the generation trajectory — the step-resolved contraction shape published independently in
2026 ([HYPOTHESES.md § Independent convergence](../HYPOTHESES.md#independent-convergence-now-prior-art)).
E3's exploratory run supports all three properties at exploratory grade; the registered replication is the
step that would settle it.

## 8. D7 — conserved quantities (E2's object), and D8 — re-closure

**D7.** `Q : ℝ^d → ℝ^k` is a **conserved quantity** of the pass iff `|Q(h_{ℓ+1}) − Q(h_ℓ)| ≤ η` along all
layers, across a declared input class — and Q is **nontrivial**: not constant on the state space and not
reducible to normalization bookkeeping (norm growth and similar normalizable dynamics are excluded, per
[H-INV](../HYPOTHESES.md#h-inv--the-forward-pass-has-conservation-laws)'s own kill condition).
H-INV requires both halves: a nontrivial Q exists, *and* its violation statistics correlate with behavioral
failure classes. Either half alone fails.

**D8.** A **boundary edit** `b → b′` induces a new trajectory and a new settled state — re-closure. The
vocabulary above distinguishes two edit levels that the program's own E5 compared behaviorally: external edits
to b (deleting claims from context — E5's Arm C, and every RAG/prompt manipulation), versus appending to b an
instruction whose *revision is executed by the model's own global re-settling* (E5's Arm B). A post-hoc
consistency note, carrying **zero verdict weight** and labeled as interpretation because it was not registered
before E5 ran: E5's registered result — external claim-level deletion injected contamination with a
retained-conclusion-lost-support signature while instructed revision did not — is the behavior expected if
conclusions are supported by globally-coupled structure that external local deletion severs and internal
re-closure re-derives ([CONCEPT.md Part II](../CONCEPT.md), necessities 2–5). This reading motivates nothing by
itself; E8 tests the instruction baseline's limits regardless of whether it is right.

## 9. What remains genuinely unavailable — open problems, named

1. **Existence, uniqueness, convergence.** A transformer is a finite composition of distinct per-layer maps,
   not an iterated contraction; nothing above guarantees a plateau exists, is unique, or is approached
   monotonically. The DEQ/Hopfield lineage ([closure-vs-dbc.md](closure-vs-dbc.md)) is positioning, not
   license — DEQs solve `x* = F(x*)` by construction; a standard transformer can only *exhibit* empirical
   plateaus (weight-tied/looped architectures are where the iterated-map reading becomes exact, and are out of
   scope). Everything above therefore **measures settling; nothing above proves it.**
2. **Operator semantics.** `constrain / release / couple / decouple / perturb / stabilize` as boundary
   transformations with laws (composition, commutation) do not exist; the "complete algebra" claim was tested
   and retired and stays retired. The vocabulary gains formal content only if operators are defined as edits on
   b with measured effects on (ℓ*, τ, V, Q) — future work, gated on the experiments that decide whether those
   quantities behave lawfully at all.
3. **The settling–correctness link.** No theorem connects ℓ*, τ, m, V, or Q to truthfulness. That connection
   is exactly what E1 and the bridge claim test empirically. Formalization cannot substitute for the
   experiments; its only legitimate role here is making their kill conditions exact.

## 10. What this document changes

- E1's free parameters `(φ, ε, w, δ)` are now named objects its pre-registration must freeze.
- One new claim is staged for registration at E1's freeze: the bridge correlation (D5) — the program's direct
  test of its own operationalization gap, with both failure directions recorded in advance.
- A terminology collision is repaired: dynamical settling-existence (E1's object) vs psychometric
  factor-existence (E0's object).
- Nothing else. No operator is added, no architecture claim is made, no result is confirmed, and the retired
  formal-mathematics claim is not resurrected: these are operational definitions, not proofs.
