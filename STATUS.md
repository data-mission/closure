# Status

The program is in execution: nine experiment protocols are published, E8 has run to verdict, E3 and E5 have
verdicts on record (E5's now under correction), and E9 (exploratory, unregistered) has run and been re-scoped.
This page states exactly what that means — what is settled, what is not, and what is deliberately not claimed
— because a stage stated plainly is worth more than a stage inferred from an absence.

Last updated: 2026-07-19.

## On the record

- **E5 — REOPENED (2026-07-19), correcting the 2026-07-16 REFUTED registered verdict.** A post-verdict
  adversarial audit (Mission X) found that the registered B-vs-C contamination separation (0.9% vs 10.3%,
  read as evidence that mechanical contraction injects contamination instructed revision avoids) **does not
  exist under a valid instrument.** The contamination metric fires on the requirement scaffold shared between
  a stale sentence and its corrected replacement, not on any real assertion of the stale conclusion. Under a
  claim-grounded replacement instrument, all three E5 arms carry ~0 real contamination (Arm-C 0/11, Arm-B
  0/1, the same flagged item appearing in both arms — direct proof the flag tracked sentence template, not
  arm behavior). `release` as formulated returns to `REOPENED`; the program has no valid measurement of an
  operator-induced revision failure. A correction note is drafted for owner review and publication:
  [CORRECTION-NOTE-DRAFT.md](experiments/E8-instruction-breakpoint/coldstart-package/x1-anatomy/CORRECTION-NOTE-DRAFT.md).
  A distinct, real, disclosed defect (not contamination): DANGLING_RULE, a completeness gap in 2/11 Arm-C items
  where contraction computes the corrected value and retains the governing rule but never draws the final
  Boolean — fix specced, gated to any future operator retest. The original registered run artifacts are
  unchanged (this is a re-interpretation of the same banked data, not a re-run); the archived snapshot DOI
  [10.5281/zenodo.21399411](https://doi.org/10.5281/zenodo.21399411) is superseded pending a new version.
  Record: [results/E5-reclosure/2026-07-15-registered-run/](results/E5-reclosure/2026-07-15-registered-run/).
- **E3 — confirmed-shaped, exploratory grade (2026-07-15).** A linear probe regressed continuous future-output
  volume from the pre-sampling hidden state (Spearman 0.83), survived within-family and length-residualization
  controls, transferred under every leave-one-family-out rotation, and beat verbalized confidence — carrying
  two honesty labels stated in full in the verdict: **unregistered** (exploratory-grade evidence by this
  program's own standard) and **threshold-fragile** on the length-residualization band. The registered
  replication (second model, fresh corpus) is the step that would settle it. Record:
  `experiments/E3-future-volume/run/VERDICT.md`, DOI
  [10.5281/zenodo.21383448](https://doi.org/10.5281/zenodo.21383448).
- **E8 — ran to verdict, registered grade (2026-07-19). Block B: no axis broke.** All gates green, zero
  flips, oracles PASS 0/12 each; workload 3,528 banked draws (filter 2,352 + Stage-2 1,176), 0 error rows.
  H-BREAKPOINT outcome (b) fired: instructed revision holds everywhere tested at practical scale — a
  program-level negative of record. The registered depth axis (A1) was found invalid as built post-verdict (an
  undisclosed polarity inversion made it measure revision success, not contamination); it was rebuilt and
  re-scored on the certified instrument (X4): no depth-breakpoint, true floor 0/447 real contamination at any
  depth. The E8 program verdict itself is unaffected — it rests on A3 (correctly polarized) and the fixed A2,
  not on A1. Record: [A1V2-DEPTH-REBUILD.md](experiments/E8-instruction-breakpoint/A1V2-DEPTH-REBUILD.md),
  Zenodo-archived Phase 0 freeze DOI
  [10.5281/zenodo.21404864](https://doi.org/10.5281/zenodo.21404864).
- **E9 — exploratory, unregistered, RUN and RE-SCOPED (2026-07-19).** Tests whether iterated
  summarize-and-continue compaction accumulates revision contamination beyond a matched no-compaction
  instruction baseline. 900/900 finals across 150 F3 families × 2 arms × 3 doses; instrument-v2 found 0/1800
  real contamination at every (arm, dose). A post-verdict adversarial re-check found the summarizer never
  reached its registered 30–50% compression band (median length ratio 0.94; 0.5% of rows in-band) and the
  band-exclusion guard was inert, so the result is re-scoped: corrections survive repeated near-lossless
  summarization at the achieved operating point; compaction at real compression ratios is untested and open.
  Record: `experiments/E9-compaction-cycles/README.md`, `PROTOCOL.md`.

## The methodological finding (Mission X)

The program's most consequential result to date is not a verdict but a discovery about its own measuring
instrument. Bidirectional DeBERTa-v3-large-MNLI entailment, used across the revision line to score whether a
model still asserts a superseded claim, fires on the requirement scaffold shared between a stale sentence and
its correction — not on any real assertion — and produces hypothesis-shaped false positives (10–26%, including
a clean rising dose-response curve that would have falsely confirmed H-COMPACT) on templated correction
corpora. It appeared five independent times in this program (E8's A2, A1, A3, E5's Arm-C, and E9's compaction
arm); all five collapsed to zero real contamination under a claim-grounded replacement instrument
(instrument-v2), which is itself certified against positive controls that must fire and adversarial hardening.
Four of the five appearances were caught by the program's own audit before any external reviewer; the fifth by
a mandatory cross-check screen built into the E9 run. Standalone statement:
[FINDING-NLI-ARTIFACT.md](experiments/E8-instruction-breakpoint/coldstart-package/mission-x/FINDING-NLI-ARTIFACT.md);
full verdict record:
[MISSION-X-VERDICT.md](experiments/E8-instruction-breakpoint/coldstart-package/mission-x/MISSION-X-VERDICT.md).
Human κ-validation of the screens (X-HUMAN, ≥100 items × 2 annotators) is staged and pending — the one
load-bearing step not yet complete.

## Published (stable, citable)

- The founding ontology, preserved as hypothesis — [CONCEPT.md](CONCEPT.md).
- The operational formal core: the definitions (settling depth, incorporation, premature closure, the bridge
  claim, future volume, conserved quantities) with their free parameters named for freezing, and the genuinely
  unformalized parts recorded as open problems — [background/formal-core.md](background/formal-core.md).
- The reduction of the ontology to falsifiable claims, and the case study of how the reduction itself went
  wrong and was corrected — [background/reduction-history.md](background/reduction-history.md).
- The living hypothesis registry: nine hypotheses bound to experiment protocols (E0–E8), plus H-COMPACT
  (exploratory, E9) and two explicitly future architectural hypotheses, each with status, confidence, and kill
  condition, the ontology's own retirement condition, and the retired claims kept visible with cause of death
  — [HYPOTHESES.md](HYPOTHESES.md).
- Nine registered experiment protocols with pre-registered verdict conditions, plus E9 (exploratory) —
  [experiments/](experiments/).
- The methodology, with every practice anchored to a standard, declared as a contribution, or listed as a known
  nonconformance with its fix — [METHODOLOGY.md](METHODOLOGY.md).
- The prior-art map and the citation-verification ledger — [background/prior-art.md](background/prior-art.md),
  [VERIFICATION.md](VERIFICATION.md).
- The frozen methodology decisions, 0001–0008 — [decisions/](decisions/).
- The research log — one entry per working session, newest last — [LOG.md](LOG.md).

## Next in line

- **The E5 correction-note publication** — owner act: venue, public status wording, whether the DANGLING_RULE
  defect is disclosed in the same note or separately. Draft ready
  ([CORRECTION-NOTE-DRAFT.md](experiments/E8-instruction-breakpoint/coldstart-package/x1-anatomy/CORRECTION-NOTE-DRAFT.md)).
- **X-HUMAN annotation** — human κ-validation of the Mission X screens (≥100 items × 2 annotators); owner-mediated
  annotator recruitment and scheduling. The one load-bearing step that converts "screened to 0" into
  "human-confirmed 0."
- **E9 real-ratio re-run** — the compaction band-enforcement fix (make the exclusion flag live, or enforce the
  30–50% band mechanically) so H-COMPACT can be tested at its registered operating point.
- **X6 re-run** — fix the corpus-construction defect (embed per-case facts) and re-run the scoped-exception
  behavioral pilot; the behavioral-form question remains open.
- **The registered E3 replication** — second model, fresh corpus, pre-frozen thresholds. The step that would
  move H-VOL from exploratory support to registered evidence.
- **S5b** — the pre-registered cross-vendor replication of E5 (pinned `gpt-5.4-mini-2026-03-17`); kills the
  same-vendor materials confound E5's protocol currently discloses.
- **E0** — API-only, CPU-only analysis; its build plan and decisions are frozen as proposals
  ([PLAN.md](experiments/E0-closure-existence/PLAN.md)), binding at pre-registration.

## Not yet run

E0, E1, E2, E4, E6, E7 — protocols published, not executed. E8 has run to verdict (Block B, no axis broke); E9
(exploratory) has run and been re-scoped; both have open follow-on regimes (X-HUMAN, X6, E9 real-ratio) listed
above.

## Built / not yet built

- **Built:** the G-slice harness ([harness/](harness/)) — the NLI grounding scalar, leave-one-out contrast,
  contamination detector, deterministic contraction, ground-truth outcome scoring, and the frozen-config
  mechanism; it served E5's registered run and E8's registered run. The claim-grounded replacement instrument,
  instrument-v2 (`experiments/E8-instruction-breakpoint/coldstart-package/x1-anatomy/instrument_v2.py`),
  certified against positive controls and adversarial hardening; it served the Mission X re-adjudication of
  E8-A3, E5-C, X4, and E9.
- **Not yet built:** R and P scoring and the factor-analysis notebook (E0), the per-layer recording harness
  (E1), the decode-time enforcement backend (E6) — each listed under "Wanted from contributors" in the
  relevant experiment folder.

## Explicitly not claimed

- That E5's original registered refutation was correct. It was withdrawn: the separation it reported does not
  exist under a valid instrument. Conversely, the corrected "instructed revision is robust" reading is itself
  scoped — one model, template-generated corpora — and does not claim the operator question is closed; harder,
  non-templated corpora remain untested.
- That E9's 0/1800 real result says anything about compaction at real compression ratios. The registered
  30–50% band was never achieved (median ratio 0.94); E9 as run measures near-lossless summarization only.
- That the Mission X screens are human-confirmed. They are agent-run, certified against positive controls and
  adversarial hardening, but the X-HUMAN κ-validation that would close the circularity of an LLM-adjacent judge
  is staged, not executed.
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

- **H-RELEASE (`release` as formulated)** — REOPENED 2026-07-19. The 2026-07-16 registered refutation is
  withdrawn: the B-vs-C separation it rested on was an NLI instrument artifact, not a real effect. See "On the
  record" above and the [correction note](experiments/E8-instruction-breakpoint/coldstart-package/x1-anatomy/CORRECTION-NOTE-DRAFT.md).
- **H-BREAKPOINT** — E8's registered run fired outcome (b): no axis broke at practical scale, a program-level
  negative of record for the instructed-revision-has-a-failure-regime question.
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

- **E8 has decided whether instructed revision has a failure regime, at practical scale, on tested corpora: it does not.** Outcome (b) fired — no axis broke. This is the program-level negative of record for
  H-BREAKPOINT; the operator line (H-ENFORCE and any reformulated H-RELEASE) has no measured opening. E9's
  compaction re-run and harder non-templated corpora remain the open ways this could still change.
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
