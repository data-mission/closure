# The Concept

**This is the founding document — the full vision, stated before any of it is proven.** Its claims are hypotheses, not results; per-claim status (open / contested / partially pre-empted / killed) lives in [HYPOTHESES.md](HYPOTHESES.md). The document is preserved close to its original form deliberately: twice already, ideas stated here were independently published by others months later ([history](background/reduction-history.md)), so the unreduced vision is kept visible rather than trimmed to what is currently defensible.

---

## Part I — The ontological stance

Why should the internal organization of a transformer care about human concepts like belief, confidence, uncertainty, explanation? Those are our ontology — not necessarily its ontology. Suppose we abandon human ontology completely. Then perhaps there isn't belief, confidence or reasoning inside at all. There is only an evolving state in an enormously high-dimensional manifold, and language is the interface through which humans interact with it — a lossy projection between geometries, like a four-dimensional object casting a two-dimensional shadow.

Nobody asks "where is redness inside a JPEG?" Redness doesn't exist in the compressed representation; it is reconstructed by the decoder. Words may work similarly:

```
latent manifold  →  language codec  →  human interpretation
```

Seven hypotheses follow from taking this seriously:

1. **The transformer is a trajectory machine.** Every forward pass is the evolution of a state; tokens, probabilities, logits are merely where we choose to observe it. Interpretability has mostly studied states; the real object may be flow — as fluid mechanics studies vector fields, not water molecules.
2. **Tokens are measurements.** Physics distinguishes the system from the measurement. If tokens are observations of a latent evolution, then asking "why did it produce this token?" resembles asking "why did the thermometer move?" — you are already looking at a measurement, not the computation.
3. **Native invariants may exist.** Humans invented energy, momentum, entropy because they stay invariant across situations. Transformers may possess analogous quantities — properties preserved during trajectory evolution — that we simply haven't discovered. Invariants are more fundamental than coordinates: coordinates change, invariants survive. *(→ [E2](experiments/E2-conserved-quantities/))*
4. **Language destroys symmetry.** Many internal trajectories may be equivalent; language forces one realization. Ten different internal evolutions may all project to "the answer is yes" — identical outside, profoundly different inside. A rich internal state is reduced to one observable.
5. **Multiple observables are possible.** We assume language is privileged because that's what we trained. Another decoder could output an object preserving geometric information that language destroys. Language may be a grayscale image of a color scene: useful, not complete. *(→ [E3](experiments/E3-future-volume/))*
6. **Reasoning traces may be shadows.** If internal evolution is continuous and chain-of-thought is discrete, the chain-of-thought may not be the computation — it may be one explanation compatible with the trajectory, as contour lines are one representation of a mountain.
7. **Discovery requires abandoning human primitives.** Every science reaches a point where inherited concepts become obstacles. "Where is memory? Where is confidence?" assumes those are primitive entities. The real primitives may be entirely different.

**The boldest speculation:** even "latent space" may be the wrong object. The important thing may not be where the state is, but how states can transform into one another — a category of transformations rather than a space of points. Meaning might not be a region of activation space; it might be an equivalence class of transformations. *(Non-operational as stated; kept as orientation, not as a claim under test.)*

## Part II — The five necessities, and the definition of closure

Starting from one observation — *language exists, therefore something inside the computation makes stable language possible* — five things follow:

1. The native evolution cannot be arbitrary; some property survives it, or no stable observable could emerge. Call it **persistent structure**.
2. Persistent structure cannot exist independently — language is not local (changing one word in a prompt sometimes changes everything). So persistent structure is **globally dependent**.
3. If every persistent structure depends on every other, nothing possesses intrinsic identity. Identity is a temporary consequence of global organization. (This is a first-principles derivation of polysemanticity.)
4. If nothing has intrinsic identity, computation cannot consist of manipulating identities. What is manipulated is **relationships** — how one persistent structure influences another.
5. Relationships cannot evolve independently: changing one changes others. So evolution must be **global reorganization** — the computation repeatedly reorganizes until the persistent structures become mutually compatible.

**Closure is the condition under which no further global reorganization changes the persistent structures relevant to the observation.** The decoder never decodes thoughts. It samples the persistent structures after this compatibility condition has approximately stabilized. Language isn't translated; language is *measured*.

Note the structural type of this concept: closure is a **generative/equilibrium** notion — the state is the fixed point `x* = F(x*)` that the computation *finds* — not a specification that an external checker *asserts*. Its true formal neighbors are equilibrium models (DEQ), Hopfield energy descent, energy-based models, and predictive coding — **not** Design by Contract, which is the checking-layer concept it is most often mistaken for. The distinction, and why it matters, is argued in [background/closure-vs-dbc.md](background/closure-vs-dbc.md).

## Part III — What follows if this is true (engineering consequences)

If closure is real, familiar categories reorganize. The founding document derived seventeen consequences; the load-bearing ones:

- **Hallucination becomes measurable as a computational event**: *premature closure* — the system reached local consistency before global consistency; the state was read out before the provided constraints were incorporated. Not a linguistic definition; a mechanical one. *(→ [E1](experiments/E1-premature-closure/))*
- **Confidence gets a computational meaning**: the volume of reachable futures. Many reachable trajectories → humans observe uncertainty; few → certainty. Reasoning becomes successive contraction of reachable trajectory space. The system does not ask the model how sure it *feels*; it measures how structurally stable the answer *is*. *(→ [E3](experiments/E3-future-volume/))*
- **Prompts, RAG, memory, tools stop being different fields.** They are all boundary conditions on one evolution — a single discipline of boundary engineering. Retrieved documents don't "inject knowledge"; they reshape the admissible closures.
- **Revision becomes an operation, not a request.** When evidence changes, you do not *ask* the model to disregard the old assumption (its trace persists in the state); you *rebuild the boundary without it* and re-close. *(→ [E5](experiments/E5-reclosure/))*
- **Uncertainty preservation becomes enforceable.** "The model is not permitted to convert unresolved structure into fluent prose" is a constraint the runtime enforces, not a hope the prompt expresses. *(→ [E4](experiments/E4-enforced-ambiguity/))*
- **Programming changes level.** You no longer specify the computation; you specify the target region of stability, and the computation finds it. Not imperative, not functional, not declarative-over-procedures — declarative over equilibria.

## Part IV — The specification layer

If the above holds, human intent compiles down to structural requirements, and structural requirements lower onto whatever control surface a model exposes:

```
Human intent
   ↓  intent compiler
Structural specification        ← the proposed abstraction layer
   ↓  model-specific lowering
Native controls (prompts, masks, retrieval, logits, steering, verifier passes)
   ↓
Model execution → closure inspection → observable rendering
```

A specification names eight kinds of structure: **boundaries** (what the computation must respect, typed by trust/persistence/revisability), **invariants** (what must survive every permitted re-closure), **preserved ambiguity** (unresolved structure that is part of the correct result), **forbidden collapses** (the failure topology: evidence blending, unsupported causality, contradiction smoothing), **grounding dependencies** (testable by removal: remove the source, re-close, if the claim survives it was never grounded), **revision rules** (what to preserve / release / re-close when evidence changes), **rigidity requirements** (conclusions must survive a declared perturbation battery), and **observables** (the projections rendered out: report, claim graph, uncertainty map).

A sketch of the surface syntax, from the founding document:

```
closure MarketAssessment {
    boundary filings        { trust authoritative }
    boundary current_news   { trust mixed; freshness required }

    invariant source_attribution
    preserve  analyst_disagreement
    forbid    invented_causality
    forbid    source_blending

    ground financials in filings

    on conflicting_evidence { preserve conflict; branch explanations }

    require rigidity main_conclusion >= 0.80
    perturb { reorder_sources; paraphrase_question; vary_decoding }

    observe as report
    observe as uncertainty_map
}
```

Six operators generate the layer: **constrain, release, couple, decouple, perturb, stabilize.** Whether they form anything like a complete algebra is *not* claimed (that claim was tested and killed — see [HYPOTHESES.md § Retired](HYPOTHESES.md#retired-claims)). Whether the layer is a *real abstraction* is an empirical question with a precise test: the same spec, lowered onto two independent enforcement backends, must produce agreeing verdicts. *(→ [E6](experiments/E6-lowering-invariance/))*

## Part V — The measurement half, available today

Four tests are implementable right now against any model API, and constitute the program's instrument (and its practical product):

| Test | Question it answers | Method |
|---|---|---|
| **G — Grounding** | "Is this claim causally supported by this source?" | Leave-one-out removal: remove the source, regenerate, measure whether the claim changes. Causal, not opinion-based. |
| **R — Rigidity** | "Does this conclusion survive rephrasing?" | Perturbation battery; classifier-compared stability. |
| **P — Preserved ambiguity** | "What is the model's output landscape on this query?" | Multi-generation semantic clustering; a diagnostic, not a gate. |
| **F — Forbidden collapse** | "Does the output contain a named prohibited pattern?" | Narrow pattern detection. |

The central hypothesis of the whole program is that these are not four unrelated functions. **They are readouts of one latent — closure quality.** That is the first thing this program tests. *(→ [E0](experiments/E0-closure-existence/))*

---

*The reduction history — how an adversarial review compressed this concept to only Part V, what that process got right, and what it dropped without disproving — is documented in [background/reduction-history.md](background/reduction-history.md). It is worth reading as a case study regardless of interest in the concept itself.*
