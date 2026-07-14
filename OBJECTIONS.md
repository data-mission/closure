# Objections

The strongest objections to this program, answered without surrender and without bluff. Each is classified:

- **misunderstanding** — the objection rests on a reading the materials don't support;
- **valid limitation** — true, acknowledged, and where possible already logged as a nonconformance;
- **open empirical question** — the objection *is* one of the experiments, by design;
- **potentially fatal** — if it holds, a load-bearing part of the program falls, and the kill condition says so;
- **requires a change** — the objection is right and points at something to fix here.

If your objection isn't here, or an answer is weak, that is a contribution — open an issue or a pull request.

---

### "This is just prompt engineering."
**Misunderstanding.** Prompt engineering searches for input phrasings that produce better outputs. This program
does the opposite: it holds the input fixed and *intervenes on it* to measure whether the output causally
depended on it — remove the source, regenerate, see if the claim changes. The unit is `given-inputs → output`
under intervention, not a prompt under optimization. Nothing here recommends how to phrase anything.

### "This is just robustness testing."
**Partly right, and that part is deliberate.** Rigidity (R) is a perturbation-robustness measurement, and the
program credits that lineage in the [prior-art map](background/prior-art.md). But robustness is one of several
readouts, and the actual claim ([H-CORE](HYPOTHESES.md)) is that grounding, rigidity, and ambiguity-preservation
are *readouts of one latent property* — a claim robustness testing has never made or tested. If that claim is
false, the program says so and the tests remain individually useful.

### "Closure is Design by Contract renamed."
**Misunderstanding, and a specific one the program already argues against.** Design by Contract is a *checking*
concept: an external assertion verifies a state it did not produce. Closure is a *generative/equilibrium* concept:
the state is the fixed point the computation itself settles into, `x* = F(x*)`. Its formal neighbors are
equilibrium models (DEQ), Hopfield energy descent, and predictive coding — not DbC. The full argument, and why
the distinction is load-bearing rather than semantic, is in [background/closure-vs-dbc.md](background/closure-vs-dbc.md).
This exact mislabeling was made once during the program's own reduction and is documented there as a type error.

### "Closure is too vague to be a scientific concept."
**Open empirical question — and the vagueness is bounded by a test, not left open.** The program does not ask you
to accept "closure" on the strength of the word. [E0](experiments/E0-closure-existence/) pins it to a single
pre-registered measurement: do the structural-quality scores collapse to one latent factor (≥60% shared variance,
same-sign loadings, surviving difficulty controls)? If they don't (pairwise |r| < 0.2), the term is retired
publicly. A concept with a scheduled execution date is not doing the work vagueness usually does.

### "Closure cannot be a single scalar."
**Open empirical question — and E0 is built to answer exactly this, including 'neither.'** E0's pre-registered
outcomes are three, not two: one factor (closure exists), no shared factor (metaphor, retire the term), or a
*partial collapse* — e.g. G and R share a factor and P does not — which is called out in the protocol as "a
meaningful, publishable answer that reshapes the concept." The scalar-vs-multidimensional question is the result,
not an assumption baked in.

### "These operators are human abstractions, not model-native primitives."
**Valid limitation, and the program has already conceded the strong form.** The claim that the six operators form
a complete algebra was *killed* under the program's own review and is kept visible in the
[retired claims](HYPOTHESES.md#retired-claims): the set grew under testing and `stabilize` had no operational
definition. What remains is weaker and testable — the operators are a working vocabulary, and whether the
*specification layer* they describe is a real abstraction is [E6](experiments/E6-lowering-invariance/)'s
falsifiable question (do independent backends agree on one spec's verdicts?). Whether any of this is "native" to
the model is not claimed; the ontological stance in [CONCEPT.md](CONCEPT.md) is labeled a stance to be tested.

### "The theory is unfalsifiable even if the individual experiments are falsifiable."
**Requires a precise answer.** There is no separate "the theory" floating above the experiments to be
independently confirmed. Every load-bearing claim is in the [registry](HYPOTHESES.md) with a kill condition, and
the founding gate — does closure exist as one object — is E0. What is *not* falsifiable is explicitly fenced as
such: the boldest ontological speculation is marked "non-operational as stated; kept as orientation, not a claim
under test," and E6b (expressiveness) is reported as an adoption A/B, not a proof. The unfalsifiable parts are
labeled unfalsifiable; the rest carries a refutation condition.

### "No experiments have run — there is nothing here yet."
**Valid, and it is the stated stage, not a defect.** [STATUS.md](STATUS.md) says plainly that no experiment has
run and that E0 is the first target. The program was published at this stage on purpose: to fix the theory and
its reduction as a public record, and to expose the protocols to attack *before* execution hardens their
assumptions. The right question at founding publication is not "why no result yet" but "is the program clear,
falsifiable, and executable enough for others to begin testing it." If the answer is no anywhere, that is a
[contribution](CONTRIBUTING.md).

### "There is too much documentation and not enough code."
**Valid tension, answered by sequencing.** The order is deliberate: pre-register the analysis plan and the
verdict conditions *before* the data, because a scorer built and tuned against real output can no longer be
honestly pre-registered ([PLAN.md](experiments/E0-closure-existence/PLAN.md)). The documentation is the frozen
plan; the code is the next step and its exact specification is written
([decisions/](decisions/), the "Wanted from contributors" lists). The shared G/R/P instrument is the highest-
leverage code contribution and is specified and waiting.

### "Existing interpretability work already covers all of this."
**Open empirical question, mapped honestly.** The [prior-art map](background/prior-art.md) credits what exists —
leave-one-out attribution, perturbation testing, semantic clustering, hidden-state dynamics — as *covered*, not
claimed. It also states what is *absent from the literature* by direct search: any factor-analytic test of the
single-latent claim (E0), any search for conserved quantities along inference depth (E2), any statement of
lowering invariance for semantic specs (E6), and the "reclosure" operation (E5). The novelty claims are narrow
and checkable; if a paper covers one of them, that is a pull request against the map.

### "Native model-to-model closure communication is fantasy."
**Valid — and it is not on the experimental program.** Non-linguistic model-to-model communication is part of the
*founding vision* in [CONCEPT.md](CONCEPT.md), and the vision is explicitly separated from the current research
program: it carries no experiment, no verdict condition, and no claim of feasibility. It is stated as the
furthest reach of the idea, labeled as such. None of the eight experiments depend on it.

### "The proposed intermediate representation can't be architecture-independent."
**Open empirical question — this is E6, stated as your objection.** [E6](experiments/E6-lowering-invariance/)
tests precisely whether the same structural specification, lowered onto two *independent* enforcement backends,
produces agreeing verdicts (≥85% agreement, κ≥0.7 confirms; <70% or unsystematic disagreement refutes and "the
compiler framing dies"). If architecture-independence fails, E6 records it. The middle outcome — a systematic map
of where "grounded" silently changes meaning between backends — is publishable either way, because no such map
exists.

### "This mixes ontology, engineering, and commercial ambition — pick one."
**Requires a framing answer, not a retreat.** The layers are real and are kept explicitly separated rather than
blended: the ontology is a stance to be tested ([CONCEPT.md](CONCEPT.md)); the engineering is the measurement
instrument, useful on its own; the consequences — where verification becomes mandatory or legally costly — are
labeled as consequences of confirmations, bought by named experiments, in the README. The program is not narrowed
to a conventional paper's scope because the connection *is* the thesis; it is organized into layers with their
epistemic status marked, which is the honest alternative to either hiding the ambition or overselling it.

---

*Classifications above are the program's own reading and are open to challenge. The place to say an answer is
wrong is an issue or a pull request against this file — recorded, with the diff visible, like everything else.*
