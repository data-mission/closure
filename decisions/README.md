# Decision records

Methodology-level choices that cut across experiments, recorded in the [MADR](https://adr.github.io/madr/)
(Markdown Any Decision Record) format — one file per decision area, numbered, never deleted.

These are distinct from the per-experiment protocols (`experiments/E*/README.md`, which register *what* each
experiment tests) and from the pre-registration itself (frozen by the registration act of [0006 as amended 2026-07-16](0006-reproducibility-and-freeze.md): public freeze commit plus Zenodo-archived release). A decision record
freezes a *how* — an operational choice an experiment's protocol leaves open — with the reasoning that fixed it,
so that a later reader can tell a deliberate choice from an oversight, and a reversal from a mistake.

## Convention
- One file per decision area: `NNNN-short-kebab-title.md`, numbered monotonically, numbers never reused.
- Status is one of: `proposed` · `accepted` · `superseded by NNNN`. A superseded record is **kept**, marked, and
  points to its replacement — it is never edited into agreement with the new decision or deleted.
- Every record states the options considered and the consequence of the chosen one, not only the choice.

## Status of this set
All records below are `proposed`. **No decision is binding until frozen by the registration act of
[0006 as amended 2026-07-16](0006-reproducibility-and-freeze.md)** (public freeze commit plus Zenodo-archived
release; see also METHODOLOGY.md nonconformance #1). Until then these record
the current best-justified choice, open to challenge like everything else in this program.

## Index
- [0001](0001-generation-and-sampling.md) — generation model, sampler, structured-output schema
- [0002](0002-grounding-measurement.md) — G: leave-one-out grounding, NLI scalar, aggregators, decorative claims
- [0003](0003-rigidity-measurement.md) — R: paraphrase generation, validity gate, stability scalar
- [0004](0004-ambiguity-measurement.md) — P: embedding model, clustering, dispersion
- [0005](0005-factor-analysis.md) — EFA library, factorability gate, parallel analysis, rotation, confound control
- [0006](0006-reproducibility-and-freeze.md) — reproducibility posture, the pre-registration freeze boundary
- [0007](0007-e5-reclosure.md) — E5 arms, contamination detector, deterministic contraction, comparison test
- [0008](0008-e8-instruction-breakpoint.md) — E8 instruction-breakpoint dose-response, Phase 0 axis selection, break definition
