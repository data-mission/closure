# Status

The program is in execution: nine experiment protocols are published, two have run to a verdict, and a third
(E8) is registered behind a gating design phase. This page states exactly what that means — what is settled,
what is not, and what is deliberately not claimed — because a stage stated plainly is worth more than a stage
inferred from an absence.

Last updated: 2026-07-16.

## On the record

- **E5 — REFUTED, registered grade (2026-07-16).** Mechanical contraction did not beat instructed disregard —
  it lost: downstream contamination 10.3% vs 0.9%, Bonferroni-corrected p = 0.0089, completeness non-inferior,
  task-level sign test agreeing (contraction worse on 9 tasks, instruction worse on 0). `release` as formulated
  is retired; the verdict is recorded in stronger-than-registered form with the pre-registration wording defect
  disclosed, not absorbed. Scope, per the commissioned hostile audit: shallow document-revision tasks (1–2
  reasoning operations); it says nothing about long contexts, stacked corrections, or deep dependency chains.
  Record: [results/E5-reclosure/2026-07-15-registered-run/](results/E5-reclosure/2026-07-15-registered-run/),
  archived snapshot DOI [10.5281/zenodo.21399411](https://doi.org/10.5281/zenodo.21399411).
- **E3 — confirmed-shaped, exploratory grade (2026-07-15).** A linear probe regressed continuous future-output
  volume from the pre-sampling hidden state (Spearman 0.83), survived within-family and length-residualization
  controls, transferred under every leave-one-family-out rotation, and beat verbalized confidence — carrying
  two honesty labels stated in full in the verdict: **unregistered** (exploratory-grade evidence by this
  program's own standard) and **threshold-fragile** on the length-residualization band. The registered
  replication (second model, fresh corpus) is the step that would settle it. Record:
  `experiments/E3-future-volume/run/VERDICT.md`, DOI
  [10.5281/zenodo.21383448](https://doi.org/10.5281/zenodo.21383448).
- **E8 — registered, not yet runnable (2026-07-16).** Derived from E5's refutation: a dose-response study on
  the instruction baseline alone, no operators anywhere. Phase 0 (axis selection) is a gating sub-registration
  that must freeze by public commit plus Zenodo-archived release before any probe is generated
  ([0008](decisions/0008-e8-instruction-breakpoint.md),
  [0006 as amended](decisions/0006-reproducibility-and-freeze.md)).

## Published (stable, citable)

- The founding ontology, preserved as hypothesis — [CONCEPT.md](CONCEPT.md).
- The operational formal core: the definitions (settling depth, incorporation, premature closure, the bridge
  claim, future volume, conserved quantities) with their free parameters named for freezing, and the genuinely
  unformalized parts recorded as open problems — [background/formal-core.md](background/formal-core.md).
- The reduction of the ontology to falsifiable claims, and the case study of how the reduction itself went
  wrong and was corrected — [background/reduction-history.md](background/reduction-history.md).
- The living hypothesis registry: nine hypotheses bound to experiment protocols (E0–E8) — one of them,
  H-RELEASE, already refuted by a registered run — plus two explicitly future architectural hypotheses, each
  with status, confidence, and kill condition, the ontology's own retirement condition, and the retired claims
  kept visible with cause of death — [HYPOTHESES.md](HYPOTHESES.md).
- Nine experiment protocols with pre-registered verdict conditions — [experiments/](experiments/).
- The methodology, with every practice anchored to a standard, declared as a contribution, or listed as a known
  nonconformance with its fix — [METHODOLOGY.md](METHODOLOGY.md).
- The prior-art map and the citation-verification ledger — [background/prior-art.md](background/prior-art.md),
  [VERIFICATION.md](VERIFICATION.md).
- The frozen methodology decisions, 0001–0008 — [decisions/](decisions/).
- The research log — one entry per working session, newest last — [LOG.md](LOG.md).

## Next in line

- **E8 Phase 0** — the axis-selection study: narrow the eight registered candidate axes, freeze the break
  definition, per-axis probe budgets, and the instrument-constraint resolution, then register by commit +
  Zenodo release ([0008](decisions/0008-e8-instruction-breakpoint.md)). The named next step.
- **The registered E3 replication** — second model, fresh corpus, pre-frozen thresholds. The step that would
  move H-VOL from exploratory support to registered evidence.
- **S5b** — the pre-registered cross-vendor replication of E5 (pinned `gpt-5.4-mini-2026-03-17`); kills the
  same-vendor materials confound E5's protocol currently discloses.
- **E0** — API-only, CPU-only analysis; its build plan and decisions are frozen as proposals
  ([PLAN.md](experiments/E0-closure-existence/PLAN.md)), binding at pre-registration.

## Not yet run

E0, E1, E2, E4, E6, E7 — protocols published, not executed. E8 is registered and gated on its Phase 0 freeze.

## Built / not yet built

- **Built:** the G-slice harness ([harness/](harness/)) — the NLI grounding scalar, leave-one-out contrast,
  contamination detector, deterministic contraction, ground-truth outcome scoring, and the frozen-config
  mechanism; it served E5's registered run.
- **Not yet built:** R and P scoring and the factor-analysis notebook (E0), the per-layer recording harness
  (E1), the decode-time enforcement backend (E6) — each listed under "Wanted from contributors" in the
  relevant experiment folder.

## Explicitly not claimed

- That E5's refutation shows instruction suffices in general. It shows instruction sufficed in the shallow
  document-revision regime tested; whether instructed revision has a failure regime at all is exactly E8's
  question, and it is open.
- That E3's result establishes H-VOL. It is exploratory-grade: unregistered, single model, threshold-fragile
  on one control band. It licenses the registered replication, not the claim.
- That the closure dimensions aggregate to a single scalar score — that is precisely what E0 tests (H-SCALAR),
  and its confidence is currently rated *low*. Whether a coherent multidimensional structural specification
  exists is a separate question, tested by E4–E7, not by E0.
- That hallucinations are solved, detected, or prevented — H-PC is `CONTESTED`, and the field itself disagrees
  on direction.
- That the true ontology of transformer inference has been discovered — the ontology is a stance stated to be
  tested, carries its own retirement condition ([HYPOTHESES.md](HYPOTHESES.md)), and is currently supported by
  one exploratory result only.
- That a structural intermediate representation (Closure IR) exists or that native model-to-model closure
  communication is possible — these are the vision's furthest reach, labeled non-operational or open.
- That a negative E0 would retire any structural claim, operator, or the IR — E0 retires only the single scalar
  score. Each architectural claim is killed only within the property its own experiment measures.
- Any adoption or external validation. None exists yet; none is implied.

## Already reduced or retired

- **H-RELEASE (`release` as formulated)** — refuted by E5's registered run, 2026-07-16: the program's first
  registered kill, recorded in stronger-than-registered form
  ([results record](results/E5-reclosure/2026-07-15-registered-run/)).
- Four claims killed under the program's own adversarial review, kept visible with cause of death: "a new
  computational paradigm," "the six operators form a complete algebra," "convergent design," and "closure
  justified by formal fixed-point mathematics" ([HYPOTHESES.md § Retired](HYPOTHESES.md#retired-claims)).
- Two founding ideas independently published by others in 2026; priority cannot be established from private
  records, so they are recorded as convergence, not prediction
  ([HYPOTHESES.md § Independent convergence](HYPOTHESES.md), [reduction history](background/reduction-history.md)).

## Next decisions, gated on results

The program has no single alive/dead gate. Each experiment directly retires only the claim it measures; broader
architectural claims survive, weaken, or die by their explicit dependencies. What survives each result is stated
in advance in the [consequence matrix](HYPOTHESES.md#consequence-matrix). In brief:

- **E8 decides whether instructed revision has a failure regime.** A break re-scopes the remaining operator
  experiments to the regime where instruction degrades (confirming none of them); no break at practical scale
  concludes the revision line with a program-level negative of record.
- **E0 decides scalar aggregation only** — whether G/R/P collapse to one closure score. A negative result retires
  the single score and reports closure as a multidimensional profile; it does **not** gate the specification
  layers. The structural hypotheses stand or fall on their own verdicts, not on E0.
- **E6 (H-LOWER) decides the portable IR.** If independent backends agree on one spec's verdicts, an
  architecture-independent Closure IR becomes plausible; if not, model-specific structural control may still
  survive, and control-plane designs that require backend portability lose support.
- **E4 and E7 each decide one operator or the compositional layer**, and are retired only within that scope.
- **E1's verdict resolves a live contradiction** in the published literature on hallucination dynamics, in
  whichever direction it lands — and carries the bridge claim
  ([background/formal-core.md](background/formal-core.md)) linking the behavioral instrument to the
  hidden-state quantities.
- **The execution control plane and native computation** are later hypotheses (H-CONTROL-PLANE, H-NATIVE) — not
  established by E0–E8, requiring their own future experiments, each governed by the same rule.
- **E6b** (the expressiveness A/B) runs only if E6 confirms — an adoption question, not a falsifiable one,
  reported as a lift; its aggregate-score portion additionally assumes a positive E0.

No timelines. Ordering is dependency and cost only ([experiments/README.md](experiments/README.md)).
