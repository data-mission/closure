# e3-0004 — E3 reproducibility standard: seeded and reported, not bit-frozen

- Status: proposed
- Deciders: closure research program contributors
- Scope: E3

This record is e3-scoped pending a merge-time renumbering into the global `decisions/` sequence (see
`README.md` in this directory).

## Context

The program's reproducibility posture (`../../../decisions/0006-reproducibility-and-freeze.md`) is
distributional-not-exact **because the provider API exposes no seed** — repeated generation reproduces the same
model and distribution, not identical draws, and the `base_seed + draw_index` field is provenance, not enforcement.
E3 runs the model **locally** through mlx-lm, which changes what is possible: every stochastic step can take an
explicit recorded seed. That is a stronger position than `0006`, and it must be stated as E3-specific so a reader
does not assume E3 inherits `0006`'s "no seed at all" limitation — nor over-reads local seeding as bit-exact
reproducibility, which it is not. This record fixes what E3 promises, what it pins, and where the freeze boundary
sits.

## Decision

- **Seeded and reported, not bit-frozen.** Every stochastic step in E3 carries an explicit, recorded seed:
  continuation sampling (`mx.random`, seed `base_seed + prompt_index * N + draw_index` per e3-0002), any numpy
  randomness, and every scikit-learn estimator with a random component (`random_state` fixed). This is **stronger**
  than `0006`'s posture — where no seed existed to record — because the draws are genuinely re-seeded, not merely
  logged. **Bit-exactness is nonetheless not promised:** Metal/GPU kernel scheduling makes floating-point reduction
  order non-deterministic across runs and across machines, so the same seed can yield activations differing in the
  low-order bits between two runs. What E3 **claims** instead: same seeds plus pinned versions produce
  **statistically equivalent results and identical verdicts**; and the **purely algorithmic** steps — the
  closed-form ridge fit on a fixed feature matrix (e3-0001) and the volume computation on fixed embeddings
  (e3-0002) — are **exactly reproducible** given the same inputs, hardware, and linear-algebra backend build —
  BLAS/LAPACK reduction order is itself a build property, so the exactness claim is scoped to the committed
  environment (`uv.lock`), not to any environment with the same seeds.

- **Pins.** Recorded in the committed e3 environment and run manifest:
  - **Generation model:** repo id `mlx-community/Qwen2.5-7B-Instruct-4bit`, snapshot revision
    `c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed` (hidden dim 3584; extraction point per e3-0001, verified 20/20 by
    the lm_head top-1 sanity check in `../FEASIBILITY.md`).
  - **Inference stack:** mlx-lm 0.31.3, with the full dependency set pinned via a committed `uv.lock` and a
    committed `.python-version` for the e3 environment.
  - **Embedding model:** `nomic-ai/nomic-embed-text-v1.5` at its pinned HF revision (e3-0002), output
    dimension pinned at 768 — the model supports Matryoshka truncation (64–768), so the dimension is a
    result-moving choice and is frozen, not defaulted.
  - **Seeds:** every seed above enumerated in a committed run manifest.
  - **Config freeze:** the full E3 configuration serialized to **sorted-key JSON** with a committed **SHA-256**
    hash, mirroring the program harness's config-freeze pattern — implemented as **new e3 files only**; the shared
    `harness/` tree is not touched by this branch.

- **Freeze boundary — same rule as `0006`.** Nothing in the E3 records is binding until the pre-registration exists
  on OSF and its external timestamp **predates** the run; a git commit is necessary but not sufficient, and a
  post-data change to any frozen E3 choice requires a *new* registration recorded alongside the original, never an
  in-place edit. Beyond `0006`'s rule, the **confirmatory run additionally requires an explicit human go** — the
  synthetic-validation stage and the primary-source citation checks (arXiv:2406.15927, arXiv:2503.14749) gate it,
  and no confirmatory datum is generated on automation alone.

## Options considered

- **Promise bit-for-bit reproducibility because E3 is local and seeded** — rejected as dishonest: local seeding
  fixes the draw *choices* but not floating-point reduction order under Metal/GPU scheduling, so two runs can
  differ in low-order bits despite identical seeds. Promising bit-exactness for the full pipeline would claim more
  than the hardware delivers; the promise is scoped to the purely algorithmic steps, where it actually holds.
- **Inherit `0006`'s distributional-only posture unchanged** — rejected as too weak: it would waste the real seed
  E3 has and understate what E3 can reproduce. `0006`'s posture is a consequence of the provider API's missing
  seed; that constraint does not bind E3, so restating it would misdescribe E3's actual guarantees.
- **Version-record the model/embedding revisions post-hoc rather than pin-and-commit them** (as `0006` permits for
  revision hashes it deems reproducibility-bookkeeping only) — rejected for E3: the probe reads a specific tensor
  of a specific checkpoint, so a silent model-revision change would move the input vector itself, not just
  bookkeeping. The revision is pinned in the freeze, not merely noted.

## Consequences

States E3's honesty line: seeded-and-reported is stronger than the program's provider-default posture on the
stochastic steps, and exact on the algorithmic ones, but the whole pipeline is **not** bit-identical across runs or
machines — a reader reproducing E3 should expect statistically equivalent results and identical verdicts, and
bit-identical output only from the ridge fit and volume computation on fixed inputs. The cost of committing
`uv.lock`, `.python-version`, the model and embedding revisions, and a SHA-256 config hash is that the E3
environment is heavier to change than a loosely versioned one — any dependency bump is a freeze-touching event that,
after registration, needs a new registration rather than an edit. That rigidity is the intended price of a
pre-registration that a later reader can check was unimpeachable at the moment the data did not yet exist.
