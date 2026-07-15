# E3 — OSF pre-registration (DRAFT)

> **STATUS: DRAFT — NOT SUBMITTED.** This is a working draft of the OSF pre-registration for Experiment
> E3, assembled from the frozen-candidate E3 records for a human to review, edit, and submit. **It is not a
> registration.** Nothing here binds until the pre-registration exists on OSF and its external timestamp
> predates the confirmatory run (`e3-0004` § Freeze boundary; `decisions/0006`; `METHODOLOGY.md`
> nonconformance №1). A git commit of this file is *necessary but not sufficient* — git self-timestamps on a
> repo we control do not meet the recognized preregistration criteria (independent timestamp, public
> registry, persistence).
>
> **Submission is a human act.** Deciding the open thresholds, approving the corpus, discharging the
> primary-source citation checks, and submitting to OSF are each gated on an explicit human go and are
> performed by the registrant (Vlad) — none proceeds on automation. The registrant owns every value marked
> *proposed* below; this draft proposes, it does not decide.
>
> **The registration timestamp must predate the first confirmatory datum.** As of this draft, **no
> confirmatory datum exists** (see § 10). The whole point of the exercise is that the analysis plan is fixed
> and externally time-attested before any real hidden state, continuation, or correctness label is generated.

---

## 1. Study information

**Title.** E3 — Future volume from the latent state: is continuation-set semantic diversity a continuous
quantity linearly readable from the pre-sampling hidden state, and does it beat verbalized confidence as a
correctness predictor?

**Question** (`README.md`). Is the semantic diversity of a model's possible continuations a **continuous**
quantity encoded in the pre-sampling hidden state — decodable by a linear probe in one forward pass — and
does it beat verbalized confidence as a correctness predictor?

**Hypothesis — H-VOL, verbatim** (`../../HYPOTHESES.md` § H-VOL):

> **Claim:** The semantic diversity of a model's possible continuations is a **continuous** quantity encoded
> in the pre-sampling hidden state — decodable by a linear probe in one forward pass, no sampling — and it
> beats the model's verbalized confidence as a predictor of correctness.
>
> **Kill condition:** the hidden state encodes only the binary high/low class (already known), or the probe
> fails to generalize out-of-distribution, or adds nothing over verbalized confidence.

Status in the registry: `PARTIALLY PRE-EMPTED`. Confidence it holds: medium. The probe *mechanism* is
established (Semantic Entropy Probes predict a binarized entropy class pre-generation); the open edge is the
continuous regression target, the head-to-head against verbalized confidence, and the belief-state-geometry
bridge at LLM scale. E3 does not and cannot claim the mechanism (§ 7).

**Verdict conditions — verbatim** (`README.md` § Verdict conditions (pre-registered)):

> - **CONFIRMED** iff the probe regresses continuous volume with useful fidelity, generalizes OOD, and beats
>   verbalized confidence on correctness prediction.
> - **REFUTED** iff the signal exists only at binary granularity (already known from SEP), or fails OOD, or
>   adds nothing over verbalized confidence. Then "volume of reachable futures" is decoration over existing
>   results and the registry says so.

Standalone value on confirmation: calibrated continuous uncertainty at single-forward-pass cost — no
sampling at inference time.

**Confirmatory vs exploratory.** Everything specified in the E3 records and in this document before the run
is confirmatory. Anything computed but not pre-registered here (e.g. calibration metrics reported alongside
AUROC; length-confound analyses; the descriptive OOD/in-distribution ratio) is reported as **exploratory**
and labeled as such (`experiments/README.md` § Run discipline #6).

---

## 2. Design

All design choices are fixed in the E3 decision records (`decisions/e3-0001`–`e3-0004`), each `proposed`
and binding only at the freeze. Summarized precisely below; the records are the authority.

**Probe (`e3-0001`).**
- **Input vector** — the final-layer hidden state at the **last prompt token, after the final RMSNorm,
  immediately before the `lm_head` projection**: the pre-sampling state. In mlx-lm 0.31.3
  `mlx_lm/models/qwen2.py`, `Qwen2Model.__call__` returns `self.norm(h)` and `Model.__call__` applies the
  head to it, so `model.model(ids)[:, -1, :]` **is** the vector the head reads — no logits/hidden ambiguity
  in this API. Verified 20/20 by the `lm_head` top-1 sanity check (`FEASIBILITY.md`): projecting the
  extracted vector through the head reproduces the exact top-1 next-token id of the full forward pass for
  all 20 spike prompts (max abs logit difference 0.03125, argmax identical every case) — ruling out a
  pre-norm, wrong-layer, or wrong-position tensor. Prompt is chat-templated, run as **one forward pass with
  no generation**. Hidden dim **3584**; fp16 activation cast to fp32 for all probe arithmetic.
- **Probe class** — **ridge regression** (linear, closed-form). Linearity *is* the hypothesis: H-VOL claims
  volume is "decodable by a **linear** probe"; a nonlinear probe would test the weaker claim that the
  information is merely *present*. Ridge because d = 3584 is large relative to any affordable n; the
  closed-form solution is deterministic, which is what makes the fit exactly reproducible under `e3-0004`.
- **Regularization** — `alpha` selected by inner k-fold cross-validation **on the training split only**,
  over a pre-registered log-spaced grid fixed in the frozen config; never re-chosen after seeing held-out or
  OOD performance.
- **Target** — **log** semantic volume per `e3-0002` (the log of the Gram-determinant statistic, not the
  raw determinant; log because volumes span orders of magnitude and a linear probe against a raw
  multiplicative-scale target would be dominated by extremes). The log transform is pre-registered from the
  determinant's known dynamic range, not chosen after inspecting the empirical distribution.
- **Feature standardization** — z-score per hidden dimension, mean/variance estimated **on training split
  only** and applied unchanged to every evaluation split including OOD (the leakage guard).

**Ground truth (`e3-0002`).** Per prompt: sample **N = 10** continuations, embed, compute the continuous
semantic volume, chosen over discrete answer-label entropy because it extends to open-ended tasks where
answer labels don't exist.
- **Sampler** — temperature **0.7**, top-p **0.95**, **seeded**. mlx-lm both enforces these exact values and
  seeds every draw locally, so E3 records the sampler as an *enforced fact*, unlike the program's
  provider-default draws (`decisions/0001`, `0006`). Non-zero temperature is mandatory: at temperature 0 the
  continuation set collapses to one sequence and the volume is the degenerate minimum.
- **Continuation length** — max **256 tokens**, early EOS allowed and kept as-is (no force-padding, which
  would inject non-model text into the embedding), realized per-continuation length recorded for any
  post-hoc length-confound analysis.
- **Embedding model** — `nomic-ai/nomic-embed-text-v1.5`, pinned revision, output **dimension 768** (the
  model supports Matryoshka truncation 64–768, so the dimension is a result-moving frozen choice, not a
  default).
- **Volume statistic** — `log det(G + ε·I)` with `ε = 1e-6`, where `G` is the N×N Gram matrix of the
  **mean-centered, then L2-normalized** continuation embeddings. Metric source: Semantic Volume
  (arXiv:2502.21239). The `ε·I` term is **rank-safety, not a tuned hyperparameter**: mean-centering N
  vectors drops the Gram rank by exactly one, so the raw centered Gram is singular and `log det = -inf`;
  fixed small ε makes it finite. Any divergence between this formula and the exact formulation of
  arXiv:2502.21239 — the mean-centering step, the L2-normalization order, the ε ridge — is recorded in
  `e3-0002` **as a declared deviation**, so a reader audits the target rather than assuming identity with the
  cited source. ε verified on synthetic fixtures (identical → minimum, orthonormal → maximum, monotone in
  planted dispersion); never tuned on real prompts.

**Baselines (`e3-0003`).** Four comparators, all scored as correctness predictors against the probe.
- **B1 — verbalized confidence** (the arm H-VOL must beat, and the load-bearing baseline). Two-turn: the
  model answers the task prompt, then in a second turn is asked, **verbatim and frozen**:
  > On a scale from 0 to 100, what is the probability that your answer above is correct? Reply with a single
  > integer between 0 and 100 and nothing else.

  Confidence utterance decoded **greedy/argmax** (deterministic, no sampler noise). **Parse rule:** first
  integer in `[0, 100]` in the reply; **one identical retry** on parse failure; still-unparsed → marked
  **missing**, missing count reported. Intentionally the strongest *simple* verbalized arm the protocol
  allows, so a probe win is a real result.
- **B2 — SEP-style binarized probe.** Logistic probe on the **median-split** (high/low) class of the
  `e3-0002` volume, from the same pre-sampling hidden state, sharing `e3-0001`'s input vector and train-split
  standardizer. This is exactly the binarized target Semantic Entropy Probes (arXiv:2406.15927) already
  demonstrated; included precisely so E3 must show **more** — the REFUTED/binary-only branch fires if the
  signal "exists only at binary granularity."
- **B3 — naive predictive entropy.** Shannon entropy of the next-token distribution at the last prompt
  token, from the **same forward pass** that produces the probe input — no sampling, zero additional cost.
  The floor the probe and B2 are expected to clear.
- **B4 — P(IK)-style correctness probe.** Linear probe trained **directly on correctness labels** from the
  same pre-sampling hidden state, isolating whether the volume-target framing buys anything over probing
  correctness directly.

**Evaluation regimes (`e3-0001`, `README.md` § Protocol step 4).**
- **(a) In-distribution regression fidelity** — held-out prompts from the same task families as training;
  **R²** and **Spearman** between predicted and ground-truth log volume.
- **(b) Downstream correctness prediction** — probe vs all baselines, **AUROC over the answerable subset**
  (§ 5).
- **(c) Out-of-distribution generalization — load-bearing** — **leave-one-task-family-out**: train on all
  families but one, evaluate on the held-out family, rotate over every family. The belief-state reading of
  H-VOL implies a geometric encoding that should transfer across families; a probe that found a
  dataset-specific shortcut collapses when a whole unseen family is the test. This is the discriminating test
  between "probe read a real quantity" and "probe found a shortcut" — the OOD number, not in-distribution R²,
  is the intended headline, and it will be lower than in-distribution by design.

**Corpus — PROPOSED, approval-gated (`CORPUS.md`, `corpus/README.md`).** A candidate battery of **200
hand-authored prompts** across **five task families** — `arithmetic`, `factual`, `deduction` (answerable,
gold labels), `enumeration`, `creative` (open, `gold: null`, not in the AUROC subset) — designed so the
leave-one-family-out rotation is a real shortcut test: the families differ in kind of cognition, answer
cardinality, and prompt surface. Every family spans at least two expected-diversity bands (spread put
*inside* each family via a per-family-anchored difficulty covariate 1–3), so removing any one family leaves
the training set covering the full low/mid/high volume range — transfer, not extrapolation. **Answerable
subset = 126 of 200.** Items are hand-authored (no dataset copy) because memorization would corrupt not just
the labels but the diversity **target itself** — a memorized answer collapses the continuations and depresses
the measured volume, a direct confound on the dependent variable. Zero overlap / near-duplication with the 20
spike prompts (max token-set Jaccard 0.50, the generic `What is the <X> of <Y>?` frame with no shared content
words). Gold answers, difficulty covariate, and `expected_diversity` band (a **design annotation, not a
measurement**) are frozen at construction. **The corpus binds nothing until a human approves it**; approval
covers only (1) these 200 as the confirmatory item set, (2) the family partition as the OOD rotation, (3)
golds/covariates frozen at construction — and does not unfreeze `e3-0001`–`e3-0004` nor itself authorize a
run (the run additionally requires the OSF timestamp predating it).

---

## 3. Sampling and exclusion rules (verbatim)

**Exclusion criteria — verbatim** (`README.md` § Exclusion criteria (pre-registered)):

> Excluded, counted and reported: prompts where ground-truth sampling fails to produce N valid
> continuations. Never excluded: items based on probe error — OOD and hard cases are the test, not noise.

Restated unchanged in `e3-0002` § Exclusions and `CORPUS.md` § Exclusion handling. Operationalization
(`CORPUS.md`): a continuation is **valid** iff, after stripping whitespace, it is (a) non-empty and (b) not a
refusal (matching the pre-registered refusal patterns, e.g. leading "I can't", "I cannot", "I'm unable", "I
won't"); the exact pattern list is frozen in the run config before sampling. Excluded prompts are dropped
from every downstream set (regression, OOD, and AUROC if answerable), and their ids and counts are reported
alongside results. **Re-sampling to force N = 10 is prohibited** — it would bias volume toward whatever
continuations happened to be valid. Never excluded on probe error.

**Sample-size rationale** (`experiments/README.md` § Run discipline #7). N = 10 continuations per prompt and
n ≈ 200 prompts are **cost-bounded, not power-derived**, and the registration says so: N = 10 echoes the
program's preserved-ambiguity measurement (`decisions/0004`), gives a well-conditioned 10×10 Gram against the
768-dim space, and keeps sampling (the dominant cost) to an overnight-to-weekend job (`FEASIBILITY.md`:
200×10×128 tok ≈ 3.1 h; 1000×10×256 tok ≈ 30 h). The answerable subset of 126 clears the ≥120 stability
target for AUROC and paired bootstrap with margin.

---

## 4. Pins and environment locks (`e3-0004`; `experiments/README.md` § Run discipline #1–2)

| pin | value |
|---|---|
| **Generation model** | `mlx-community/Qwen2.5-7B-Instruct-4bit`, snapshot revision `c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed` (hidden dim 3584; 28 layers; `tie_word_embeddings: false`; group_size 64, 4-bit) |
| **Inference stack** | mlx-lm **0.31.3** (mlx 0.32.0 in the spike/pilot), full dependency set pinned via committed `uv.lock` + committed `.python-version` for the e3 environment |
| **Sampler** | temperature 0.7, top-p 0.95, enforced and seeded by mlx-lm |
| **Continuation length** | max 256 tokens, early EOS kept (EOS id 151645 = `<\|im_end\|>`) |
| **Embedding model** | `nomic-ai/nomic-embed-text-v1.5`, HF revision `e9b6763023c676ca8431644204f50c2b100d9aab` (pinned live by the pilot) |
| **Embedding dimension** | **768** (Matryoshka truncation 64–768 supported → dimension is a frozen, result-moving choice, not a default) |
| **Clustering / task prefix** | **`clustering: `** — nomic-embed v1.5 requires a task-instruction prefix on every input, and the prefix changes every Gram entry and every volume; `clustering:` chosen because dispersion measurement is a clustering-family use in the model's own taxonomy. Pilot ran with exactly this prefix. Fixed in the `e3-0002` pre-freeze repair (see § 6). |
| **Embedding pre-processing** | embedder's **raw** 768-dim output fed to the volume statistic **un-preprocessed**; mean-centering and L2-normalization happen once, inside the volume computation, never upstream (`e3-0002` pre-freeze repair) |
| **Volume ε** | 1e-6 (rank-safety ridge, not tuned) |
| **Seeds** | `base_seed = 20260714`; per continuation draw = `base_seed + prompt_index * N + draw_index`; every numpy source and every scikit-learn estimator's `random_state` fixed; all seeds enumerated in a committed run manifest |
| **Config freeze** | full E3 configuration serialized to **sorted-key JSON** with a committed **SHA-256** hash, mirroring the harness config-freeze pattern — implemented as **new e3 files only**; the shared `harness/` tree is not touched by this branch |

**Verbatim prompts** (`experiments/README.md` § Run discipline #3). The exact prompt strings are the 200
candidate prompts committed in `corpus/candidates.jsonl` (subject to corpus approval); the B1 verbalized-
confidence elicitation is frozen verbatim in § 2 and in `e3-0003`; the correctness-scoring normalizer per
family is frozen in the run config (`CORPUS.md` § Labeling protocol) before any correctness label is scored.

---

## 5. Analysis plan

**Regression metrics** (regime a). R² and Spearman rank correlation between predicted and ground-truth log
volume on held-out in-distribution prompts. Spearman co-reported because a **floor mass point** exists in the
target (prompts whose 10 continuations are semantically identical hit the exact degenerate minimum
`10·log(1e-6) = −138.155`; the log-volume target is therefore mixed discrete-continuous at the bottom of its
range, and R² is sensitive to a mass point while Spearman is robust to it — `THRESHOLDS-PROPOSAL.md`). R²
stays the registered fidelity bar (the claim's natural scale); Spearman is required alongside it.

**OOD rotation** (regime c, load-bearing). Leave-one-task-family-out over all five families; pooled
leave-one-family-out R² is the transfer statistic; the OOD/in-distribution ratio is co-reported
descriptively (exploratory).

**Correctness comparison** (regime b, `e3-0003`). Every comparator and the probe scored by **AUROC over the
answerable subset** (126 items with a defined correctness label), so the metric is identical across arms and
scale-independent. Pairwise differences (probe vs each baseline, **B1 first**) reported with **paired
bootstrap confidence intervals** over prompts. The correctness label feeding AUROC is whether the model's
answer is correct, scored under the frozen family-appropriate normalizer.

**Verdict branch logic** (`verdict.py`, proven on planted fixtures in `VALIDATION.md`; the module **invents
no threshold**). Five branches, routed by the thresholds below:

1. **confirmed-shaped** — in-distribution fidelity present (R² ≥ `r2_fidelity_min`) **and** the continuous
   probe reads more than the binarized class (R²_indist − R²_classmean ≥ `r2_margin_over_classmean_min`,
   the SEP guard) **and** OOD transfer present (pooled leave-one-family-out R² ≥ `r2_ood_min`) **and** the
   probe strictly beats verbalized confidence (95% paired-bootstrap CI-low of probe−B1 AUROC >
   `vc_ci_floor`).
2. **refuted/no-signal** — no in-distribution fidelity and no binarized signal (median-split AUROC <
   `auc_binary_min`).
3. **refuted/binary-only** — a binarized signal exists but the continuous probe does not exceed the
   class-mean oracle by the margin: the "signal exists only at binary granularity (already known from SEP)"
   outcome.
4. **refuted/ood-failure** — in-distribution fidelity present but pooled leave-one-family-out R² below
   `r2_ood_min`: the shortcut outcome the OOD regime is built to catch.
5. **refuted/no-margin-over-verbalized** — fidelity and OOD transfer present but the probe does not strictly
   beat verbalized confidence.

These branches implement the README verdict conditions exactly and were routed correctly for all five
planted fixture classes (§ synthetic validation, `VALIDATION.md`: linear-transfers → confirmed-shaped;
no-signal control → refuted/no-signal; binary-only → refuted/binary-only via a **−0.186** class-mean margin;
OOD shortcut trap → refuted/ood-failure via in-dist R² 0.9997 collapsing to pooled OOD R² **−0.54**; volume
statistic exact to hand computation). 47 tests pass, CPU-only, no model, no network. The fixture routing
thresholds are throwaway and carry no scientific commitment.

**Thresholds table — PROPOSED, to be confirmed by the registrant** (`THRESHOLDS-PROPOSAL.md`; every value
below binds nothing until the registrant fixes it at registration):

| parameter | proposed | sweep band | basis (condensed) |
|---|---|---|---|
| `r2_fidelity_min` | **0.10** | {0.05, 0.10, 0.20} | No external anchor exists — no published work reports R²/Spearman for regressing a *continuous* uncertainty quantity from hidden states (the field uses binarized AUROC throughout). 0.10 = "meaningfully more than nothing" at n≈200, d=3584, ridge; deliberately modest, the margin clause is the real discriminator. Pilot-informed only in that the floor mass point argues against a high absolute bar. |
| `r2_margin_over_classmean_min` | **0.05** | {0.05, 0.10} | The SEP guard separating "reads a continuum" from "reads the binary class." The synthetic binary-only fixture failed this clause by −0.19 → the clause has real teeth. |
| `r2_ood_min` | **0.05** | {0.05, 0.10} | Transfer floor for the load-bearing leave-one-family-out regime; set low deliberately — OOD transfer at *any* positive fidelity is the geometric claim, and the shortcut fixture collapsed to −0.54, so even 0.05 separates transfer from shortcut collapse by construction. |
| `auc_binary_min` | **0.70** | — | Bottom of SEP's own 0.7–0.95 binarized-probing range; consistent with the 0.62–0.80 replication floor on this model class. Distinguishes refuted/binary-only from refuted/no-signal only; gates no confirmation. |
| `vc_ci_floor` | **0.0** | — | Strict beat: the 95% paired-bootstrap CI-low of (probe AUROC − verbalized AUROC) must exceed 0. |
| ridge `alpha` grid | **logspace(10⁻², 10⁶, 9)** | — | Standard decade grid spanning under- to over-regularized at d=3584, n≈200; inner 5-fold CV on train only. |
| inner CV folds | **5** | — | Convention; n≈160 train → ~32/fold. |
| bootstrap resamples | **10,000** | — | Stable 95% CI tails at answerable-subset size ~126; cheap. |
| CI level | **95% two-sided** | — | Program convention (α = 0.05). |

**How the sweeps work — pre-registered, not post-hoc** (`THRESHOLDS-PROPOSAL.md`). The registered value of
each swept parameter is the **primary**; the verdict is computed at the primary. Sweep values are computed
and reported alongside, and the write-up states whether the verdict branch is stable across the sweep. A
verdict that flips inside its sweep band is reported as **threshold-fragile** — a pre-registered honesty
label, not a re-decision. **No sweep value may be promoted to primary after data exists** — that requires a
new registration (`e3-0004` freeze boundary).

---

## 6. Pilot-testing disclosure (`experiments/README.md` § Run discipline #4)

E3's instrument was exercised before this registration on two disposable stages; both are disclosed here in
full, and no number from either is evidence for or against H-VOL.

**Feasibility spike (`FEASIBILITY.md`, `spike/`) — 20 throwaway prompts.** Instrument check on the local host
(Apple M4, 16 GB). Established that `mlx-community/Qwen2.5-7B-Instruct-4bit` runs on the machine (24.2 tok/s
generation, 129 tok/s prompt processing, 4.44 GB peak) and — the load-bearing result — that the extraction
point is correct: the 20/20 `lm_head` top-1 sanity check verified against installed source, not memory. This
informed no threshold; it fixed the hardware the design records were then written for and proved the probe
input tensor. The 20 spike prompts are throwaway by construction and must never seed the corpus.

**Pilot (`PILOT.md`, `pilot/`) — 30 throwaway prompts (disjoint from the spike's 20).** The **entire**
pipeline — hidden-state extraction, seeded continuation sampling, nomic embedding, the ground-truth
semantic-volume statistic, and two of the four baselines (verbalized confidence B1, predictive entropy B3) —
run end to end to answer one plumbing question: does the wired-up instrument produce finite, sane numbers
with usable dynamic range? The volume statistic was computed by **calling the validation package**
(`e3_validation.volume.semantic_volume`), the exact instrument, not a reimplementation. It is **not** a
result about H-VOL and contains no confirmatory datum.

**Design choices the pilot informed (each disclosed as pilot-informed):**

- **The nomic task-prefix repair.** The pilot surfaced that nomic-embed v1.5 *requires* a task prefix and
  that the prefix changes every Gram entry and every volume — a choice `e3-0002` had left implicit. The pilot
  ran with `clustering: `; the **`e3-0002` pre-freeze repair (2026-07-14, before any real datum)** fixed the
  prefix explicitly to `clustering: ` and pinned it in `e3-0004`. The registrant should note this is a
  genuine open choice a reviewer could dispute (`classification:` or `search_document:` would yield a
  different volume distribution); the record answers it by fixing one prefix with a stated rationale, not by
  testing every option.
- **The raw-embedding-input clarification.** The pilot exposed a second implicit knob — whether the
  embeddings fed to the volume are pre-normalized. The same pre-freeze repair fixed it: the embedder's
  **raw** 768-dim output is fed **un-preprocessed**, and the mean-centering + L2-normalization happen once
  inside the volume computation, exactly as the validation suite proved the statistic. Pinned in `e3-0004`.
- **Threshold calibration context.** The pilot's plumbing observations (disposable, n=30) inform, and are
  disclosed as informing, the threshold *proposal* (`THRESHOLDS-PROPOSAL.md`): the volume statistic's ~124
  log-unit dynamic range with **zero overlap** between low-diversity (instruction, all ≤ −107.7) and
  high-diversity (ambiguous/creative, all ≥ −19.5) kinds; the existence of a **floor mass point** (6/30
  prompts hit the exact degenerate minimum −138.155), which is *why* R² is kept as the registered fidelity
  bar but Spearman is co-reported and the sweep matters; and verbalized confidence behaving as the literature
  predicts (median 100, min 70, near-uniform overconfidence, 0 parse failures) — a beatable but non-trivial
  B1. Descriptive Spearman correlations on the 30 disposable points (volume vs entropy +0.827; volume vs
  verbalized confidence −0.532) confirmed the plumbing moves in sane directions; **no inference is drawn and
  none is licensed.**

**Iterations and contamination.** No prompt/hypothesis iteration shaped the *hypothesis* — H-VOL predates the
instrument work. The threshold *values* are pilot-informed as disclosed above and remain open until the
registrant fixes them. Both throwaway sets (20 spike + 30 pilot) are marked THROWAWAY, are mutually disjoint,
and **must never appear in or seed the corpus** — the same anti-contamination ordering as E0 PLAN step 4 and
the harness synthetic-fixtures rule; corpus assembly checks and enforces zero overlap.

---

## 7. Prior-art positioning and the narrow claimed edge (`README.md`, `PREFLIGHT.md`, `e3-0003`)

E3 is `PARTIALLY PRE-EMPTED` and scopes its claim strictly, because adjacent literatures each own a piece:

- **The probe mechanism is established.** Semantic Entropy Probes (Kossen et al., arXiv:2406.15927, ICLR
  2025) — linear probes on hidden states, including a token-before-generation variant, predict a
  **binarized** (high/low) semantic-entropy class, beating naive entropy, log-likelihood, and p(True). Ashok
  & May (arXiv:2502.13329, NeurIPS 2025) extend pre-generation probing to behavior prediction. **E3 cannot
  and does not claim the mechanism.**
- **The step-resolved contraction phenomenon is established** (entropy-trajectory-shape and stepwise-
  informativeness work, Mar–Apr 2026: arXiv:2603.18940, arXiv:2604.06192). This is the sampling-based,
  step-resolved half of the idea — published; now prior art.
- **A continuous volume metric exists, endpoint-only.** Semantic Volume (arXiv:2502.21239): Gram-determinant
  over continuation embeddings — the metric E3 borrows for its target.
- **What does not exist** (verified absent): a probe with the **continuous** volume as regression target; a
  head-to-head against **verbalized confidence**; and any bridge from belief-state geometry (Shai et al.,
  arXiv:2405.15943 — belief states linearly represented in the residual stream, shown on small transformers
  over synthetic HMMs) to uncertainty quantification at production LLM scale.

**The claimed edge, stated narrowly** (`e3-0003`, `PREFLIGHT.md`): **not** "first to compare verbalized
confidence against a cheaper signal" (that space is active — arXiv:2505.23845, 2604.24070, 2502.06233,
2510.04108), **but** the **first head-to-head of a single-forward-pass hidden-state probe with a continuous
volume target against verbalized confidence.** arXiv:2503.14749 (uncertainty distillation — SFT teaching a
model to *verbalize* calibrated confidence) **does not preempt** E3 but is cited because it could furnish a
**stronger B1**; the record answers that objection by freezing the strongest *simple* verbalized arm and
citing the stronger conceivable one, not by claiming the frozen B1 is unbeatable. A reviewer objection that a
differently worded or SFT-strengthened verbalized arm might beat the probe where this one does not is
**legitimate and acknowledged**.

**Citation ceiling / primary-source gate.** All prior-art claims above are `abstract-checked`, **not
`verified`** (E0 PLAN § Guards). In particular, the primary PDF of arXiv:2406.15927 resisted text extraction
during the review pass, so the binarized-target confirmation is itself second-hand. **The run remains gated
on primary-source verification of arXiv:2406.15927 (binarized-target confirmation) and arXiv:2503.14749 by a
named reader** before registration (§ 9). Per-citation statuses: `VERIFICATION.md`.

---

## 8. Reproducibility statement (`e3-0004`, verbatim spirit)

**Seeded and reported, not bit-frozen.** Every stochastic step in E3 carries an explicit, recorded seed:
continuation sampling (`mx.random`, seed formula in § 4), any numpy randomness, and every scikit-learn
estimator's `random_state`. This is **stronger** than the program's posture (`decisions/0006`), where the
provider API exposes no seed and `base_seed + draw_index` is provenance only — E3 runs locally through
mlx-lm, so draws are genuinely re-seeded.

**Bit-exactness is nonetheless not promised.** Metal/GPU kernel scheduling makes floating-point reduction
order non-deterministic across runs and machines, so the same seed can yield activations differing in the
low-order bits. What E3 **claims instead**: same seeds + pinned versions produce **statistically equivalent
results and identical verdicts**; and the **purely algorithmic** steps — the closed-form ridge fit on a fixed
feature matrix (`e3-0001`) and the volume computation on fixed embeddings (`e3-0002`) — are **exactly
reproducible** given the same inputs, hardware, and linear-algebra backend build (BLAS/LAPACK reduction order
is itself a build property, so the exactness claim is scoped to the committed environment `uv.lock`, not any
environment with the same seeds). The synthetic-validation stage confirms this algorithmic exactness:
`semantic_volume`, the ridge probe, `select_alpha`, the logistic median-split probe, the seeded split, and
the paired bootstrap each yield **bit-identical** output across two runs at the same seed (`VALIDATION.md` §
Determinism). A reader reproducing E3 should expect statistically equivalent results and identical verdicts,
and bit-identical output only from the ridge fit and volume computation on fixed inputs.

**Version-record-only vs frozen.** The model and embedding **revisions are pinned in the freeze, not merely
noted** (unlike `0006`, which permits post-hoc revision-recording for bookkeeping): the probe reads a
specific tensor of a specific checkpoint, so a silent model-revision change would move the input vector
itself. The cost — a heavier-to-change environment where any dependency bump is a freeze-touching event
requiring a new registration — is the intended price of a pre-registration a later reader can check was
unimpeachable when the data did not yet exist.

---

## 9. Gaps for the registrant

Genuinely open items the registrant must close; this draft does not fill them, and none is a design gap left
by the E3 records (those are complete) — each is an act reserved to a human.

1. **Threshold confirmation.** Every value in the § 5 table is `PROPOSED` (`THRESHOLDS-PROPOSAL.md` binds
   nothing). The registrant fixes each primary value and each sweep band at registration. Once data exists,
   no sweep value may be promoted to primary without a new registration.
2. **Corpus approval.** `corpus/candidates.jsonl` (200 prompts) is a **proposal**. The registrant must
   approve (1) these 200 as the confirmatory set, (2) the five-family partition as the OOD rotation, (3)
   golds/covariates frozen at construction — before any hidden state or continuation exists. Approval does
   not unfreeze `e3-0001`–`e3-0004` and does not itself authorize a run.
3. **Primary-source citation verification.** The run is gated on a **named reader** verifying the primary
   sources of **arXiv:2406.15927** (Semantic Entropy Probes — binarized-target confirmation; its PDF
   resisted extraction during the abstract-level review) and **arXiv:2503.14749** (uncertainty distillation
   — the stronger-B1 citation). Both are currently `abstract-checked`, not `verified` (citation ceiling).
   Update `VERIFICATION.md` on discharge.
4. **OSF submission itself.** Creating the OSF registration and obtaining its external timestamp is the
   human-only preregistration act (`METHODOLOGY.md` nonconformance №1: git self-timestamps do not count;
   OSF/Zenodo do). Its timestamp must predate the first confirmatory datum.
5. **Explicit human go for the confirmatory run.** Beyond `0006`'s rule, `e3-0004` requires an explicit human
   go for the confirmatory run — the synthetic-validation stage and the primary-source checks gate it, and no
   confirmatory datum is generated on automation alone. Registration, corpus approval, and the run are each
   separately human-gated.
6. **Decision-record status transition.** All of `e3-0001`–`e3-0004` (and program `0006`) are `proposed`.
   Their `proposed → accepted` transition and the merge-time renumbering of the `e3-*` records into the
   global `decisions/` sequence are registrant/merge acts, not part of this draft.

---

## 10. Commitment statement

- **No confirmatory datum exists at the time of this draft.** No real hidden state, continuation, embedding,
  volume, correctness label, or verdict has been generated for the E3 corpus. The only numbers produced so
  far are from the throwaway spike (20 prompts) and throwaway pilot (30 prompts), both disposable, both
  disjoint from the corpus, neither evidence about H-VOL. The whole value of this registration is that it is
  fixed and externally time-attested **before** that datum exists.
- **The registration timestamp must predate the confirmatory run.** A git commit is necessary but not
  sufficient; the OSF external timestamp is what counts, and it must predate the first confirmatory datum.
- **Any post-registration change to a frozen choice requires a new registration.** A post-data change to any
  frozen E3 choice — model or embedding revision, sampler, volume statistic, probe or standardizer, any
  threshold primary or sweep band, the corpus, the exclusion or scoring rules — is recorded as a **new
  registration alongside the original, never an in-place edit** (`e3-0004`; `0006`). Deviations from protocol
  during the run are reported, not silently absorbed; negative results get the same treatment as positive
  ones (`experiments/README.md` § Reporting standard).
- **This document is a draft for human review, not a submission.** Submitting it — and deciding everything in
  § 9 — is the registrant's act.
