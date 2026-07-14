# Status

The program is at its starting line: the theory, its adversarial reduction, the hypotheses with their kill
conditions, the methodology, and the eight experiment protocols are published; empirical execution is beginning.
This page states exactly what that means — what is settled, what is not, and what is deliberately not claimed —
because a stage stated plainly is worth more than a stage inferred from an absence.

Last updated: 2026-07-13.

## Published (stable, citable)

- The founding ontology, preserved as hypothesis — [CONCEPT.md](CONCEPT.md).
- The reduction of that ontology to falsifiable claims, and the case study of how the reduction itself went
  wrong and was corrected — [background/reduction-history.md](background/reduction-history.md).
- The living hypothesis registry: ten active hypotheses — eight with current experiment protocols (E0–E7) and
  two explicitly future architectural hypotheses (the control plane and native computation) — each with status,
  confidence, and kill condition, plus the retired claims kept visible with cause of death
  — [HYPOTHESES.md](HYPOTHESES.md).
- Eight experiment protocols with pre-registered verdict conditions — [experiments/](experiments/).
- The methodology, with every practice anchored to a standard, declared as a contribution, or listed as a known
  nonconformance with its fix — [METHODOLOGY.md](METHODOLOGY.md).
- The prior-art map and the citation-verification ledger — [background/prior-art.md](background/prior-art.md),
  [VERIFICATION.md](VERIFICATION.md).
- The execution plan and the frozen methodology decisions for the gating experiment —
  [experiments/E0-closure-existence/PLAN.md](experiments/E0-closure-existence/PLAN.md), [decisions/](decisions/).

## Ready to implement now

- **The shared G/R/P measurement instrument.** Buildable today against any model API; it serves five of the
  eight experiments and stands on its own regardless of whether the closure hypothesis holds. This is the
  highest-leverage engineering contribution available ([CONTRIBUTING.md](CONTRIBUTING.md)).
- **E0** (the gating experiment) and **E5** — API-only, CPU-only analysis, days of work each once the instrument
  and corpora exist.

## In preparation (decisions frozen, awaiting execution)

- E0's build-and-run plan and its methodology decisions are written and frozen as proposals; they become binding
  when E0 is pre-registered ([decisions/](decisions/), [PLAN.md](experiments/E0-closure-existence/PLAN.md)).

## Not yet run

- **Every experiment.** No experiment has been executed; there are no results. E0 is the first target
  ([results/](results/) is empty by design). "No result yet" is the expected state at founding publication, not
  an omission — the program was published so that the plan can be attacked before execution hardens its
  assumptions.

## Not yet built

- The shared G/R/P harness, the difficulty-annotated task batteries, the factor-analysis notebook, the per-layer
  recording harness (E1), and the decode-time enforcement backend (E6) — each is listed under "Wanted from
  contributors" in the relevant experiment folder.

## Explicitly not claimed

- That the closure dimensions aggregate to a single scalar score — that is precisely what E0 tests (H-SCALAR),
  and its confidence is currently rated *low*. Whether a coherent multidimensional structural specification
  exists is a separate question, tested by E4–E7, not by E0.
- That hallucinations are solved, detected, or prevented — H-PC is `CONTESTED`, and the field itself disagrees
  on direction.
- That the true ontology of transformer inference has been discovered — the ontology is a stance stated to be
  tested, not a finding.
- That a structural intermediate representation (Closure IR) exists or that native model-to-model closure
  communication is possible — these are the vision's furthest reach, labeled non-operational or open.
- That a negative E0 would retire any structural claim, operator, or the IR — E0 retires only the single scalar
  score. Each architectural claim is killed only within the property its own experiment measures.
- Any empirical result, any adoption, any external validation. None exists yet; none is implied.

## Already reduced or retired

Four claims were killed under the program's own adversarial review and are kept visible with cause of death:
"a new computational paradigm," "the six operators form a complete algebra," "convergent design," and
"closure justified by formal fixed-point mathematics" ([HYPOTHESES.md § Retired](HYPOTHESES.md#retired-claims)).
Two founding ideas were independently published by others in 2026; priority cannot be established from private
records, so they are recorded as convergence, not prediction
([HYPOTHESES.md § Independent convergence](HYPOTHESES.md), [reduction history](background/reduction-history.md)).

## Next decisions, gated on results

The program has no single alive/dead gate. Each experiment directly retires only the claim it measures; broader
architectural claims survive, weaken, or die by their explicit dependencies. What survives each result is stated
in advance in the [consequence matrix](HYPOTHESES.md#consequence-matrix). In brief:

- **E0 decides scalar aggregation only** — whether G/R/P collapse to one closure score. A negative result retires
  the single score and reports closure as a multidimensional profile; it does **not** gate the specification
  layers. The structural hypotheses (E4–E7) stand or fall on their own verdicts, not on E0.
- **E6 (H-LOWER) decides the portable IR.** If independent backends agree on one spec's verdicts, an
  architecture-independent Closure IR becomes plausible; if not, model-specific structural control may still
  survive, and control-plane designs that require backend portability lose support.
- **E4/E5/E7 each decide one operator or the compositional layer**, and are retired only within that scope.
- **The execution control plane and native computation** are later hypotheses (H-CONTROL-PLANE, H-NATIVE) — not
  established by E0–E7, requiring their own future experiments, each to be governed by the same rule.
- **E1's verdict resolves a live contradiction** in the published literature on hallucination dynamics, in
  whichever direction it lands.
- **E6b** (the expressiveness A/B) runs only if E6 confirms — an adoption question, not a falsifiable one,
  reported as a lift; its aggregate-score portion additionally assumes a positive E0.

No timelines. Ordering is dependency and cost only ([experiments/README.md](experiments/README.md)).
