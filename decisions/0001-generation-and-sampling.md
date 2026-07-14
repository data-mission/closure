# 0001 — Generation model, sampler, and structured-output schema

- Status: proposed
- Deciders: closure research program contributors
- Scope: E0, E1, E5, E6, E7 (any experiment that generates model output to be scored)

## Context
The experiment protocols say "one fixed model" and "structured output so claims are pre-decomposed at generation
time" but do not pin the model, the decoding parameters, or the output schema. Each is a choice that changes the
numbers the scoring produces, so each must be fixed before any data is generated and recorded here.

## Decision
- **Generation model:** one pinned frontier model with a stable version identifier and structured-output support.
  Candidates: `claude-sonnet-5` or `claude-opus-4-8` (dateless identifiers are fixed snapshots under the
  provider's no-silent-update policy; `claude-haiku-4-5-20251001` is available if an explicit dated string is
  preferred). Tier is a cost/capability choice to be fixed at freeze; `claude-sonnet-5` is the working default
  (structured output, current default tier, lower cost for short answers; long-context capacity is irrelevant to
  these tasks).
- **Sampler (shared across G, R, P):** originally temperature 0.7, top-p 0.95. Non-zero is mandatory — at
  temperature 0 the preserved-ambiguity dispersion is identically 0 and rigidity is identically perfect, collapsing
  two constructs. The same sampler is used for every score so cross-indicator comparison is valid.
  **Pre-registration repair (before any pilot call):** the pinned tier's API surface rejects explicit sampling
  parameters, so the 0.7/0.95 values cannot be sent. The registered sampler is the provider default (stochastic,
  non-zero), which satisfies the non-degenerate-dispersion rationale above; thinking is explicitly disabled to keep
  generation single-pass across arms and the output budget clean. Both are recorded in the frozen config
  (`sampling = "provider-default"`, `thinking = "disabled"`) and therefore in the freeze hash. This repair was made
  before any generation call, so no data predates it.
- **Structured-output schema:** `{claims: [{id, text, source_ids: [int]}], conclusion: str}`. One claim = one
  atomic proposition; `source_ids` records which provided inputs a claim draws on; an empty `source_ids` marks a
  structurally decorative claim (see 0002). This schema is a program design, not extracted from a standard — the
  experiment protocols require structured decomposition but do not specify its shape.
- **Seed:** `base_seed + draw_index` is logged **as a provenance field only**. The provider API does not expose a
  seed parameter, so this is not API-enforced determinism (see 0006).

## Consequences
Fixes the cost basis (the K and N multipliers in 0002–0004 apply to this model at these settings) and the unit of
scoring (one atomic claim). The schema choice is the one most exposed to challenge; it is recorded here as a
proposal so a reviewer can object to it directly rather than infer it from code.
