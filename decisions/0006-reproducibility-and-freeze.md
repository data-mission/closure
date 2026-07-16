# 0006 — Reproducibility posture and the pre-registration freeze boundary

- Status: proposed
- Deciders: closure research program contributors
- Scope: all experiments

## Context
The program's credibility rests on the analysis plan being fixed before the data is seen (METHODOLOGY.md
nonconformance #1: E0 pre-registered on OSF before its first run; git self-timestamps do not count). Two facts
have to be stated plainly for that to be honest: what "reproducible" can and cannot mean here, and exactly which
choices are frozen at what moment.

## Decision
- **Reproducibility is distributional, not exact, for generated text.** The provider's API exposes no seed
  parameter, so repeated generation at a fixed temperature does not reproduce identical draws — it reproduces the
  same model and the same distribution. The `base_seed + draw_index` field (0001) is a provenance log, not an
  enforcement mechanism. Any claim of exact regeneration is scoped only to purely algorithmic steps (e.g. E5's
  contraction in 0007), never to LLM draws.
- **The freeze boundary.** Every result-sensitive choice in 0001–0005 (and 0007 for E5) is frozen at a named git
  commit before any generation, **and that git commit is necessary but not sufficient** — the actual
  pre-registration act is the OSF submission, whose external timestamp is what counts. A run may not begin until
  the OSF registration exists and predates it; a post-data change to any frozen choice requires a *new*
  registration recorded alongside the original, never an in-place edit.
- **Scope of the freeze:** the model and sampler (0001), the schema (0001), every scoring formula and threshold
  (0002–0004), the full analysis including the factorability gate and partialling method (0005), and E5's arms,
  detector, and comparison test (0007). Version-record-only (safe to note post-hoc): the NLI/embedding revision
  hashes, the K and N counts, and the library version — these change reproducibility bookkeeping, not the result.

## Amendment — 2026-07-16 (registration act redefined)

E5 ran gated by freeze-by-public-commit alone, without an OSF deposit; the deviation is recorded in its
results record (`results/E5-reclosure/2026-07-15-registered-run/`, GATE-RECORD.md) rather than absorbed.
That run exposed the gap between this record's original wording and the program's practice, and the gap is
resolved here rather than left ambiguous for E8:

- **The registration act, from this amendment forward:** every result-sensitive choice frozen at a named
  public commit on origin, **plus a Zenodo-archived tagged release of that frozen state, both predating the
  first generation.** The Zenodo DOI supplies the independent external timestamp (it meets the
  independent-timestamp / public-registry / persistence criteria in METHODOLOGY.md's own reference; the
  repository's Zenodo integration is operational — see the E3 verdict DOI). A run may not begin until the
  release exists; a post-data change to any frozen choice requires a new registration recorded alongside
  the original, never an in-place edit.
- **OSF becomes optional**, an additional deposit where wanted, no longer the required act. The original
  Decision bullet's sentence "the actual pre-registration act is the OSF submission" is superseded by this
  amendment.
- **Applies to E8 and everything after.** E8's Phase 0 freeze therefore means: Phase 0 content committed,
  tagged, and Zenodo-archived before any probe generation.

## Consequences
Sets the honesty line the whole program depends on: the verdict is worth exactly as much as the pre-registration
was unimpeachable at the moment the data did not yet exist. It also states a real limitation (no exact LLM
reproducibility) up front rather than letting a reader assume more than the tooling can deliver. The 2026-07-16
amendment keeps that line while replacing the third-party act (OSF) with one the program demonstrably executes
(commit + Zenodo-archived release), so the gate is defined by what is verifiable rather than by what was planned.
