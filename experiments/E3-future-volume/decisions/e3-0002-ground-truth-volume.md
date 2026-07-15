# e3-0002 — Ground-truth semantic volume: sampling, embedding, and the volume statistic

- Status: proposed
- Deciders: closure research program contributors
- Scope: E3

This record is e3-scoped pending a merge-time renumbering into the global `decisions/` sequence (see
`README.md` in this directory).

## Context

The E3 protocol (`../README.md` § Protocol step 1) defines the ground truth as: per prompt, "sample N
continuations, embed, compute the continuous semantic volume (Gram determinant per 2502.21239)." It fixes the
metric family and the open-ended-task rationale but leaves N, the sampler and its seeding, the continuation length
budget, the embedding model, and the exact volume formula unfixed. This ground truth is the regression target for
the probe of e3-0001; every choice here directly moves that target and therefore every downstream R², Spearman, and
correctness number, so each must be fixed before the first real continuation is generated.

## Decision

- **N = 10 continuations per prompt.** Echoes the N = 10 of the program's preserved-ambiguity measurement
  (`../../../decisions/0004-ambiguity-measurement.md`), keeping the sampling budget consistent across the program.
  Ten mean-centered, L2-normalized embedding vectors in the ~768-dimensional nomic space give a 10×10 Gram matrix
  that is well-conditioned relative to that ambient dimension, and cost is linear in N, so 10 buys a stable
  determinant without a superlinear sampling bill (`../FEASIBILITY.md` cost projection: 200 prompts × 10 × 128 tok
  ≈ 3.1 wall-clock hours on the local host). **Sensitivity to N** is checked only on synthetic fixtures and the
  pilot — never on confirmatory data: N is pre-registered at 10, and any N-sweep runs against planted fixtures and
  disposable pilot prompts so it can never be tuned to move a real result.

- **Sampler: temperature 0.7, top-p 0.95, seeded.** These are the values `0001` originally intended for the whole
  program but could not enforce, because the pinned provider API rejected explicit sampling parameters and the
  registered sampler became "provider-default" (see `../../../decisions/0001-generation-and-sampling.md` and its
  pre-registration repair). E3 runs the model locally through mlx-lm, whose backend both **enforces** the exact
  0.7/0.95 values and **seeds** every draw, so E3 records the intended sampler as an enforced fact rather than a
  logged intention. Seed per draw = `base_seed + prompt_index * N + draw_index`, recorded in the run manifest
  (e3-0004). The non-zero temperature is mandatory for the same reason the program required it: at temperature 0
  the continuation set collapses to a single sequence and the semantic volume is identically the degenerate minimum,
  which would destroy the very quantity being measured.

- **Continuation length: max 256 tokens, early EOS allowed, actual lengths recorded.** The 256-token cap bounds
  cost (`../FEASIBILITY.md` throughput of 24.2 tok/s makes 256 the ceiling used in its longer projection);
  continuations that hit EOS earlier are kept as-is rather than force-padded, because padding to a fixed length
  would inject non-model text into the embedding. Per-continuation realized length is recorded so that any
  length-confound analysis (short answers embedding closer by construction) can be run post hoc.

- **Embedding model: `nomic-ai/nomic-embed-text-v1.5`, pinned revision, output dimension 768.** The same
  embedder the program's preserved-ambiguity measurement pins (`../../../decisions/0004-ambiguity-measurement.md`),
  for the same reasons: program consistency (one sentence-embedding space across experiments) and CPU viability on
  the local host. This model supports Matryoshka truncation (64–768 dimensions), which would change every Gram
  entry, so the output dimension is fixed here at the full 768 — a frozen choice, not a library default. The
  revision is pinned in e3-0004 and version-recorded, not silently tracked.

- **Volume statistic: log-determinant of the Gram matrix of the mean-centered, L2-normalized embeddings, with a
  pre-registered ridge term.** For a prompt's N continuation embeddings: mean-center the N vectors, L2-normalize
  them, form the N×N Gram matrix `G` of their inner products, and take `log det(G + epsilon * I)` with
  `epsilon = 1e-6`. The metric source is Semantic Volume (arXiv:2502.21239), a Gram-determinant over continuation
  embeddings. The `epsilon * I` ridge is **rank-safety, not a tuned hyperparameter**: mean-centering N vectors
  drops the Gram rank by exactly one, so the raw centered Gram is singular and its log-determinant is `-inf`; a
  fixed small epsilon makes the determinant finite without materially moving the well-conditioned directions.
  Epsilon is pre-registered at 1e-6 and its effect is verified on synthetic embedding sets (identical vectors →
  minimum volume; orthonormal → maximum; monotone in planted dispersion), never tuned on real prompts. Any
  divergence between this formula and the exact formulation of arXiv:2502.21239 — the mean-centering step, the
  L2-normalization order, and the epsilon ridge in particular — is recorded here **as a deviation** so a reader can
  see precisely where E3's statistic departs from the cited source rather than assuming identity.

- **Exclusions (mirroring the E3 protocol verbatim).** Excluded, counted, and reported: prompts where ground-truth
  sampling fails to produce N valid continuations. **Never excluded on probe error** — OOD and hard cases are the
  test, not noise, and dropping items because the probe predicts them badly would select the confirmatory set on
  the outcome. This restates `../README.md` § Exclusion criteria unchanged.

## Options considered

- **Larger N (e.g. 20–30) for a smoother determinant** — rejected as the registered value: cost is linear in N and
  the 10×10 Gram is already well-conditioned against the ~768-dim embedding space; the marginal stability does not
  justify doubling or tripling an already overnight-to-weekend sampling job. N remains at 10 with the sweep confined
  to fixtures and pilot.
- **Discrete answer-label entropy (semantic-entropy clustering) as the ground truth** — rejected by the protocol
  itself: it does not extend to open-ended tasks where discrete answer labels do not exist, which is the exact
  reason `../README.md` chose the continuous volume. Recording it here would contradict the protocol.
- **Raw determinant with no ridge term** — rejected: mean-centering makes the centered Gram exactly rank-deficient,
  so `det = 0` and `log det = -inf` for every prompt; the pipeline would produce no finite target at all. The
  epsilon ridge is the minimal fix and is declared as rank-safety, not tuning.
- **Centroid-distance or mean-pairwise-distance dispersion instead of the Gram determinant** — not used as the E3
  target: the protocol registers the Gram-determinant volume specifically because it is a *continuous* quantity
  spanning open-ended tasks, and the program's separate dispersion measures already live in `0004`. E3's novel
  claim is the volume target; substituting a dispersion scalar would forfeit it.

## Consequences

Defines the regression target of e3-0001 as one finite scalar per prompt — `log det(G + 1e-6 I)` over 10 seeded,
enforced-sampler continuations embedded in the pinned nomic space. The highest-exposure choice is the seeded
enforced sampler: because E3 can enforce and seed 0.7/0.95 where the program could not, its ground truth is a
stronger artifact than the program's provider-default draws — but that also means E3's numbers are **not** directly
comparable to the program's provider-default measurements, and any cross-experiment comparison must account for the
different (enforced vs default) sampler. The centering-plus-epsilon volume formula is a deliberate, declared
deviation from the cited metric's exact form; stating it as a deviation is what lets a reader audit the target
rather than assume it is arXiv:2502.21239 unchanged. The N = 10 budget makes ground-truth sampling the dominant
cost of the whole experiment (probe-input extraction is ~4 minutes for 1000 prompts by comparison), and that cost is
paid at train time only — at inference the probe reads one forward pass with no sampling, which is the standalone
value the protocol claims on confirmation.
