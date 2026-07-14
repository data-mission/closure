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

## Consequences
Sets the honesty line the whole program depends on: the verdict is worth exactly as much as the pre-registration
was unimpeachable at the moment the data did not yet exist. It also states a real limitation (no exact LLM
reproducibility) up front rather than letting a reader assume more than the tooling can deliver.
