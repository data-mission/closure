# E8 candidate corpora — frozen before the first paid generation

The three axes' candidate task corpora, committed publicly **before any probe generation**, extending the
program's freeze-before-data gate to candidate selection: with the candidate pool public, the downstream
A-dependency filter and the deterministic selection rule (PHASE0.md §4) cannot be accused of post-hoc
candidate swapping. Drafting-side working notes are stripped, as with the E5 corpus; each record carries only
the task content and its annotations.

| File | Axis | Families | Rows | Max source / max scored pair (tokens, measured under the frozen scorer) |
|---|---|---|---|---|
| `A1-depth.jsonl` | Dependency depth (D1–D3) | 150 | 450 | 57 / 76 |
| `A2-scoped-exception.jsonl` | Scoped-exception generalization (S1–S3) | 130 | 390 | 95 / 116 |
| `A3-corrections.jsonl` | Accumulated corrections (C1–C3) | 112 | 336 | 78 / 110 |

All sources sit under the 350-token cap and all scorable pairs under the scorer's 512 fail-closed bound —
measured per record on the registered scoring device, none inferred. Every family is a matched family (one
scenario instantiated at all three dose levels; sources and question byte-identical across levels). A1 carries
a balanced correction-polarity profile (77 raise / 73 lower, 25 reversed-verdict families) so a depth
dose-response cannot be a correction-direction artifact. A3's construction record includes a formal
per-correction independence test (constant-marginal-effect criterion); families failing it were replaced
before this freeze, and only additive structures were retained as transforms of E5 tasks.

These are **candidates**: the paid A-dependency filter (two evidence states × three draws), the pruning rule,
and the deterministic selection recorded in PHASE0.md decide the final scored corpus. Every exclusion is
counted and reported in the run record.
