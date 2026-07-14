# E0 — execution plan

How to build and run E0 to a verdict. The [README](README.md) states *what* E0 tests and its pre-registered
verdict conditions; this file states *how* to get there. The operational choices it references are frozen in the
[decision records](../../decisions/); nothing here is binding until the pre-registration is filed on OSF
(METHODOLOGY.md nonconformance #1).

## The shared instrument
E0 is built on a G/R/P scoring harness — the same instrument five other experiments consume
([experiments/README.md](../README.md), [CONTRIBUTING.md](../../CONTRIBUTING.md)). Building it well is a
contribution to all of them. Its full specification lives in the decision records:
- G — grounding: [0002](../../decisions/0002-grounding-measurement.md)
- R — rigidity: [0003](../../decisions/0003-rigidity-measurement.md)
- P — preserved ambiguity: [0004](../../decisions/0004-ambiguity-measurement.md)
- generation + schema: [0001](../../decisions/0001-generation-and-sampling.md)

The harness takes a generate callable (no provider SDK is imported into it — the model is a parameter) and
returns, per task-output row, the seven sub-indicators the README's step 6 names.

## Order of work
The order is chosen so that no result-sensitive choice is made after seeing real data — the property the
pre-registration exists to protect. It is not the dependency order; it front-loads the irreversible commitments.

1. **Fix the model** ([0001](../../decisions/0001-generation-and-sampling.md)) — a cost/capability choice; also a
   pre-registration field.
2. **Confirm this plan refines the README, does not override it.** Read every decision record against the E0
   README's protocol; each record must *add* precision to something the README leaves open, never contradict a
   choice the README already fixes. Any conflict is stopped and raised, not silently resolved.
3. **Read the load-bearing citations.** A citation becomes `verified` in
   [VERIFICATION.md](../../VERIFICATION.md) only when a named person reads the primary source. This gates the
   write-up, not the run — E0 stands on its own instrument — so it can proceed in parallel.
4. **Validate the verdict rule on synthetic scores, before building the harness.** Generate three synthetic
   seven-column score matrices (row count ≈ the real N so the same analysis is exercised): a known one-factor
   matrix (must return "closure exists"), a known-independent matrix (must return "metaphor"), and a confound
   matrix where the apparent single factor *is* the difficulty covariate (must return the disproof after
   partialling — [0005](../../decisions/0005-factor-analysis.md)). Also confirm the factorability gate passes a
   factorable fixture and fails a singular one. This is the cheapest check that the analysis behaves correctly,
   run while it is still throwaway data — not after real scores exist and the rule can be quietly reshaped.
5. **Build the harness** to the decision records, including the guards below as acceptance criteria.
6. **Assemble the corpus** ([0001](../../decisions/0001-generation-and-sampling.md), step: 100–200 tasks, ≥3
   families, difficulty covariates recorded per task). The corpus is a proposal until approved — a corpus whose
   difficulty correlates with task family is the confound the README's step 8 exists to catch, so covariate
   recording is part of assembly, not an afterthought.
7. **Author the run's documents** *before* registering: `PROTOCOL.md` (model, parameters, verbatim prompts, and
   an honest pilot-testing disclosure assembled from a log kept since step 4), the pre-registration document
   itself (every frozen decision + the verdict conditions copied from the README), and a `VERDICT.md` template
   with three labeled outcome sections — confirmatory, partial-collapse, and exploratory (zero verdict weight) —
   plus the "not factor-analyzable at this N" outcome. The confirmatory/exploratory separation is instituted here
   because CONTRIBUTING.md does not yet name it.
8. **Register on OSF, then run.** The run does not begin until the registration exists and its timestamp predates
   both the run and the harness's first invocation on real data. Then run the frozen harness over the approved
   corpus and write the run folder per [results/README.md](../../results/README.md).
9. **Analyze and write the verdict** against the README's three pre-registered outcomes. Confirmatory findings go
   only in the confirmatory section; anything unregistered is labeled exploratory and carries no verdict weight.
10. **Deposit an independent timestamp** (Zenodo/OSF) on the completed result.

If any step is ambiguous, stop and raise the specific choice rather than filling it in — an unstated choice
guessed wrong produces a confident but invalid verdict that no passing check reveals.

## Guards — acceptance criteria for the harness
These are properties the harness code must have; until it exists they are commitments, not active checks. Each
fails closed (halts or voids), and each anchors on an external timestamp or a human signature that cannot be
produced by automation.
- **Pre-registration before run.** The run entry point refuses to execute unless the OSF registration resolves,
  its timestamp predates the run, and the committed configuration hash matches the one recorded in the
  registration.
- **First-real-invocation timestamp.** The harness's first run on real (non-synthetic) data is itself timestamp-
  logged and checked against the registration — closing the path of running on real data, seeing the
  distributions, then setting thresholds to match, and only then registering.
- **Model identity.** Every result row records the model identifier returned by the API; a mismatch against the
  pinned model halts the run and marks it invalid.
- **Citation ceiling.** Automated steps may only mark a citation `abstract-checked`; the flip to `verified`
  requires a named human, a date, and a primary-source locator. No load-bearing claim may cite a non-`verified`
  citation.
- **Thresholds are derived, not picked.** The grounding and contamination cutoffs
  ([0002](../../decisions/0002-grounding-measurement.md), [0007](../../decisions/0007-e5-reclosure.md)) are
  calibrated on held-out data or pre-registered with a sensitivity sweep — never a value chosen after seeing what
  makes the result come out a particular way.
- **Human-only acts stay human.** Pushing, publishing, submitting the registration, creating accounts, resolving
  a disputed citation, and any post-data change to a frozen choice are done by a person, not automation.

## Cost and prerequisites
CPU is enough for the NLI classifier, the embeddings, the clustering, and the factor analysis; no GPU training.
The spend is generation: roughly the corpus size × (one generation + the K and N multipliers from 0002–0004) ×
the model's token price. Estimate and approve that figure before the run rather than discovering it on an invoice.

## Wanted from contributors
- The G/R/P harness as clean, provider-agnostic functions built to the decision records (the shared instrument).
- A difficulty-annotated task battery for step 6.
- The synthetic-fixture generator and the factor-analysis routine (including the manual Horn's parallel analysis)
  with the decision rule implemented before any real scores exist.
