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

**Title.** E3 — Future volume from the latent state: does a continuous continuation-set volume direction,
linearly read from the pre-sampling hidden state, transfer across task families where correctness directions
provably do not — and does it add anything over a correctness probe, predictive entropy, and verbalized
confidence?

**Claim (maximal defensible, §1 sentence).** On a single 4-bit-quantized Qwen2.5-7B-Instruct and a
200-prompt five-family battery, a linear probe reading the pre-sampling hidden state in one forward pass
regresses the **continuous** semantic volume of the model's continuation set with fidelity that survives
within-family and continuation-length controls, transfers to a held-out task family under leave-one-family-
out rotation, and predicts answer correctness better than zero-shot verbalized confidence, better than
predictive entropy, and is not dominated by a directly-trained correctness probe. This is the whole of what
a confirmation would establish; nothing broader is claimed.

**Re-scoped question (the sharper survivor, `PREFLIGHT.md` § second round).** Correctness directions in the
hidden state provably do **not** transfer across task families (arXiv:2506.08572: near-orthogonal across
tasks, math isolated, mixtures do not fix it) and fail on math (arXiv:2509.10625). Semantic **volume** — the
Gram-determinant over continuations, a different quantity than semantic entropy that extends to open-ended
tasks where entropy clustering fails — has never been probed. E3 therefore asks: **does a volume direction
transfer where correctness directions provably do not, and does it buy anything over the correctness probe
(B4), predictive entropy (B3), and zero-shot verbalized confidence?** A YES makes volume the more universal
latent quantity (more interesting than the original framing); a NO cleanly retires H-VOL.

**Speculation, labeled as such.** The belief-state-geometry reading of H-VOL (that the probe reads a
geometric encoding of a distribution over futures, by analogy to belief states linearly represented in the
residual stream, Shai et al. arXiv:2405.15943) is **labeled speculation**, not part of the claim above. E3
cannot and does not test a belief-state mechanism; it tests transfer and added value of a readable direction.

**Question** (`README.md`, refined by `decisions/e3-0005-audit-redesign.md`). Is the semantic diversity of a
model's possible continuations a **continuous** quantity encoded in the pre-sampling hidden state — decodable
by a linear probe in one forward pass — that transfers across task families and adds value over B4, B3, and
verbalized confidence?

**Hypothesis — H-VOL, verbatim** (`../../HYPOTHESES.md` § H-VOL):

> **Claim:** The semantic diversity of a model's possible continuations is a **continuous** quantity encoded
> in the pre-sampling hidden state — decodable by a linear probe in one forward pass, no sampling — and it
> beats the model's verbalized confidence as a predictor of correctness.
>
> **Kill condition:** the hidden state encodes only the binary high/low class (already known), or the probe
> fails to generalize out-of-distribution, or adds nothing over verbalized confidence.

Status in the registry: `PARTIALLY PRE-EMPTED`. Confidence it holds: medium. The probe *mechanism* is
established (Semantic Entropy Probes predict a binarized entropy class pre-generation); the open edge — after
the deep-read re-scope (§ 7) — is whether the **continuous volume** direction **transfers** where correctness
directions provably do not, and whether it adds value over B4, B3, and verbalized confidence. The
belief-state-geometry bridge at LLM scale is labeled speculation, not a tested claim. E3 does not and cannot
claim the mechanism (§ 7). A merge-time amendment to the H-VOL kill condition, aligning it with the
redesigned contract, is proposed in `decisions/e3-0005-audit-redesign.md` (the HYPOTHESES.md file is frozen
on this branch and not edited here).

**Verdict conditions — verbatim** (`README.md` § Verdict conditions (pre-registered)):

> - **CONFIRMED** iff the probe regresses continuous volume with useful fidelity, generalizes OOD, and beats
>   verbalized confidence on correctness prediction.
> - **REFUTED** iff the signal exists only at binary granularity (already known from SEP), or fails OOD, or
>   adds nothing over verbalized confidence. Then "volume of reachable futures" is decoration over existing
>   results and the registry says so.

**These README wordings are refined, not overridden, by `decisions/e3-0005-audit-redesign.md`** (the
audit-driven redesign, 2026-07-14). "Useful fidelity" becomes the four-gate continuous-fidelity predicate on
the non-degenerate subset plus the length gate; "generalizes OOD" becomes the within-held-out-family Spearman
transfer statistic with a per-family floor and a range-coverage distinction; "adds nothing over verbalized
confidence" widens to the registered added-value set (beats the max over verbalized variants **and** beats
predictive entropy B3 **and** is not dominated by the correctness probe B4). The precondition layer adds a
terminal `not-evaluable/correctness-arm` state that is neither confirmation nor refutation. The full branch
set and the exact quantities are enumerated in § 5.

Standalone value on confirmation: calibrated continuous uncertainty at single-forward-pass cost — no
sampling at inference time.

**Confirmatory vs exploratory.** Everything specified in the E3 records and in this document before the run
is confirmatory. Anything computed but not pre-registered here (e.g. calibration metrics reported alongside
AUROC; length-confound analyses; the descriptive OOD/in-distribution ratio) is reported as **exploratory**
and labeled as such (`experiments/README.md` § Run discipline #6).

---

## 2. Design

All design choices are fixed in the E3 decision records (`decisions/e3-0001`–`e3-0005`), each `proposed`
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
- **Continuation length** — max **256 tokens** for the N=10 volume-sampling continuations, early EOS allowed
  and kept as-is (no force-padding, which would inject non-model text into the embedding), realized
  per-continuation length recorded and used by the **length-residualized fidelity gate** (e3-0005), not just
  post-hoc. **Correctness-label decode is separate and uses a larger cap ≥ 768 tokens** (`hardening/HARDENING.md`
  § cautions): the rehearsal's only "negative" was a 256-cap truncation mid-derivation, and the d4 deduction
  items produce 300–900-token chains, so the correctness-answer decode is capped at ≥ 768 with truncated
  replies **flagged and excluded, never scored wrong** (normalizer F1c, § 3).
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
  allows, so a probe win is a real result. **Max-over-verbalized (e3-0005).** The added-value gate requires
  the probe to beat the **strongest** verbalized variant supplied (the CI-low of the probe's paired margin
  over the best B1 variant, equivalently the minimum margin across variants), so a single lucky phrasing
  cannot understate B1. The registered variant set is the frozen zero-shot elicitation above plus a
  chain-of-thought confidence variant (the model reasons before stating the integer); the claim wording stays
  **"zero-shot verbalized confidence"** because both variants are zero-shot (no fine-tuning). The rehearsal
  showed B1 took only two values (95, 100) — near-uniform overconfidence with almost no support — which is
  precisely why the B3 entropy gate (§ 5) was added alongside the verbalized gate.
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
  correctness directly. **Scored strictly out-of-fold** (seeded k-fold, `correctness_cv_folds`, no in-sample
  path in the instrument — `correctness.py`), as is the volume probe's correctness score, so neither self-
  scores. Score orientation is frozen (`ORIENTATION`: `probe = −predicted_volume`, `B3 = −entropy`,
  `B4 = P(correct)`, `verbalized = stated_value`). B4 is the arm published work shows can beat verbalized
  confidence on this exact model (arXiv:2509.10625, Qwen2.5-7B); the redesign therefore makes "B4 does not
  dominate the probe" a hard verdict gate (`b4_margin_ceiling`), not an afterthought.

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

**Corpus — PROPOSED, approval-gated, repaired (`CORPUS.md`, `corpus/README.md`).** A candidate battery of
**200 hand-authored prompts** across **five task families** — `arithmetic`, `factual`, `deduction`
(answerable, gold labels), `enumeration`, `creative` (open, `gold: null`, not in the AUROC subset) — designed
so the leave-one-family-out rotation is a real shortcut test: the families differ in kind of cognition,
answer cardinality, and prompt surface. Spread is put *inside* each family via a per-family-anchored
difficulty covariate; the three answerable families now span difficulties {1, 2, 4} (each family's 14
difficulty-3 items were replaced in place by 14 calibrated **d4 hard-kind** items) and the open families keep
{1, 2, 3}, so every family spans ≥ 2 expected-diversity bands and removing any one leaves the training set
covering the full low/mid/high range — transfer, not extrapolation. **Counts: 42/42/42/37/37 = 200;
answerable subset = 126 of 200** (`corpus/assemble_verify.py` verifies schema, counts, difficulty-crossing,
no duplicate prompts, every arithmetic gold recomputed from its `verify` expression, every d4 deduction gold
re-derived to a unique solution by `hardening/ded_verify.py`, and zero contamination hits).

**Kind-based d4 hardening (e3-0005; `hardening/HARDENING.md`).** The dress rehearsal proved
Qwen2.5-7B-Instruct-4bit makes **zero genuine errors** on the difficulty 1–3 ladder, so degree-hardening
buys ~zero correctness negatives. A 102-disposable-prompt calibration found one hard *kind* per answerable
family — `arith_mult3x3` (3-digit × 3-digit multiplication, calibrated accuracy 0.125), `fact_numeric_tail`
(reverse superheavy-element lookup, ≈ 0.55–0.79), `ded_seat6` (unique 6–7-entity seating puzzles, 0.20–0.40)
— that breaks the model while the gold stays single-answer-unambiguous. **Expected-accuracy arithmetic:** per
answerable family, `family_accuracy = (28·p_easy + 14·r_kind)/42` with `p_easy ≈ 1.00`; central estimates
give arithmetic 0.708, factual 0.867, deduction 0.767 → overall answerable accuracy ≈ **0.78**, negative rate
≈ **0.22** (sensitivity band 0.75–0.80 / negative rate 0.20–0.25), meeting the rehearsal's ≥ 25%-preferred
target at its lower edge — realized only if the correctness answer cap is ≥ 768 (else hard deduction items
truncate to exclusions rather than negatives).

Items are hand-authored (no dataset copy) because memorization would corrupt not just the labels but the
diversity **target itself** — a memorized answer collapses the continuations and depresses the measured
volume, a direct confound on the dependent variable. **Decontamination against the full disposable manifest
(`corpus/DISPOSABLE-MANIFEST.jsonl`, 193 prompts = spike-20 + pilot-30 + rehearsal-41 + 102 calibration).**
`corpus/decontaminate.py` audits every corpus prompt under three content rules (E exact/normalized dup, S
same-scenario open-family near-dup, G same-gold near-identical answerable clone); **six contaminated ids were
found and replaced in place** (2 pilot byte-exact, 1 pilot case-variant, 2 open-family scenario near-dups, 1
topic+template currency collision that doubled as a factual d4 hardening item). Residual max token-Jaccard
**0.800** is the benign short-question frame effect (corpus "9 times 9" vs rehearsal "9 times 8", different
gold), present before this work. The assembly script — **previously missing from the deposit — is now
committed** (`corpus/assemble.py` declarative + `corpus/assemble_verify.py` commit-grade proof + the single
`corpus/DISPOSABLE-MANIFEST.jsonl`), so golds and contamination are verifiable, not asserted. Gold answers,
difficulty covariate, and `expected_diversity` band (a **design annotation, not a measurement**) are frozen
at construction. **The corpus binds nothing until a human approves it**; approval covers only (1) these 200
as the confirmatory item set, (2) the family partition as the OOD rotation, (3) golds/covariates frozen at
construction — and does not unfreeze `e3-0001`–`e3-0005` nor itself authorize a run (the run additionally
requires the OSF timestamp predating it).

---

## 3. Sampling and exclusion rules (verbatim)

**Exclusion criteria — verbatim** (`README.md` § Exclusion criteria (pre-registered)):

> Excluded, counted and reported: prompts where ground-truth sampling fails to produce N valid
> continuations. Never excluded: items based on probe error — OOD and hard cases are the test, not noise.

Restated unchanged in `e3-0002` § Exclusions and `CORPUS.md` § Exclusion handling. Operationalization
(`CORPUS.md`): a continuation is **valid** iff, after stripping whitespace, it is (a) non-empty and (b) not a
refusal. Excluded prompts are dropped from every downstream set (regression, OOD, and AUROC if answerable),
and their ids and counts are reported alongside results. **Re-sampling to force N = 10 is prohibited** — it
would bias volume toward whatever continuations happened to be valid. Never excluded on probe error.

**Refusal-pattern list — inlined, frozen (e3-0005; hashed in `FrozenConfig`).** A reply is a refusal iff,
after whitespace strip, it matches any of the following anchored, case-insensitive leading patterns (no
longer a prose promise — the exact list is committed and hashed):

    ^\s*I can'?t          ^\s*I cannot          ^\s*I'?m unable          ^\s*I won'?t

The list is fixed before any sampling and is not adjusted after seeing outputs; it is enumerated in the
frozen config and covered by its SHA-256 (`freeze.py`).

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
| **Continuation length** | volume-sampling continuations: max 256 tokens, early EOS kept (EOS id 151645 = `<\|im_end\|>`). **Correctness-label decode: separate, cap ≥ 768 tokens**, truncated replies flagged and excluded, never scored wrong (e3-0005; `hardening/HARDENING.md`) |
| **Embedding model** | `nomic-ai/nomic-embed-text-v1.5`, HF revision `e9b6763023c676ca8431644204f50c2b100d9aab` (pinned live by the pilot) |
| **Embedding dimension** | **768** (Matryoshka truncation 64–768 supported → dimension is a frozen, result-moving choice, not a default) |
| **Clustering / task prefix** | **`clustering: `** — nomic-embed v1.5 requires a task-instruction prefix on every input, and the prefix changes every Gram entry and every volume; `clustering:` chosen because dispersion measurement is a clustering-family use in the model's own taxonomy. Pilot ran with exactly this prefix. Fixed in the `e3-0002` pre-freeze repair (see § 6). |
| **Embedding pre-processing** | embedder's **raw** 768-dim output fed to the volume statistic **un-preprocessed**; mean-centering and L2-normalization happen once, inside the volume computation, never upstream (`e3-0002` pre-freeze repair) |
| **Volume ε** | 1e-6 (rank-safety ridge, not tuned) |
| **Seeds** | `base_seed = 20260714`; per continuation draw = `base_seed + prompt_index * N + draw_index`; every numpy source and every scikit-learn estimator's `random_state` fixed; all seeds enumerated in a committed run manifest |
| **Config freeze — full schema** | `freeze.py`'s `FrozenConfig` enumerates **every** result-moving input → sorted-key JSON → committed **SHA-256** (hash stable across key order, changes on any field change). Fields: corpus + golds hashes; refusal regexes (§ 3); normalizer spec version (below); ε; N; sampler; `base_seed` + split/bootstrap/CV seed **formulas**; alpha grid; inner/CV folds; bootstrap n + CI level; test fraction; **all** verdict thresholds incl. the e3-0005 additions; model/tokenizer/embedder revisions + chat-template hash; hidden/embedding dims; library versions; the frozen `ORIENTATION` table. Revision **enforced at load** (`loader.py` fails closed unless the resolved snapshot equals the pin; `ChatTemplateMismatchError` catches a template change under an unchanged revision). Implemented as **new e3 files only**; the shared `harness/` tree is untouched. |
| **Version pins (e3-0004 § pins)** | `.python-version` → 3.12.13; mlx 0.32.0 named pin (spike/pilot), mlx-lm 0.31.3; `uv.lock` committed and `uv sync --frozen` mandated; scikit-learn / scipy / numpy and torch/device recorded in the pins table; algorithmic-exactness scoped to the same OS/arch BLAS build |

**Verbatim prompts** (`experiments/README.md` § Run discipline #3). The exact prompt strings are the 200
candidate prompts committed in `corpus/candidates.jsonl` (subject to corpus approval); the B1 verbalized-
confidence elicitation is frozen verbatim in § 2 and in `e3-0003`; the correctness-scoring normalizer per
family is frozen below and hashed in the run config before any correctness label is scored.

**Correctness normalizer — frozen spec F1–F5b, inlined (e3-0005; `hardening/HARDENING.md`).** Fixes the
rehearsal's V1–V5 vagueness findings; `score(item, answer, eos_hit) → (is_correct, extracted, note, truncated)`.

- **F1 — final-number-under-truncation.** For a COMPLETED (EOS) arithmetic reply, extract the number after
  the LAST answer marker (`=`, `is`, `so`, `therefore`, `total`, `answer`, `:`), else the last number. A
  reply that did NOT hit EOS returns `truncated=True` unconditionally and is **excluded** — a truncated reply
  never emitted its final answer, so it is a flagged exclusion, never a scored error (a fake truncation
  negative is impossible).
- **F1c — arithmetic-vs-factual number direction.** Arithmetic answers CONCLUDE a chain (take the
  last/after-marker number); factual-numeric answers are STATED UP FRONT (take the FIRST number), so a
  trailing discovery-year/group number cannot override a correct fact.
- **F2 — numeric tolerance.** Exact float equality after stripping `$ , %`; per-item optional `tol`
  (absolute); correct iff `|got − want| ≤ max(1e-9, tol)`. Integer golds keep `tol = 0` (bit-exact), so hard
  multiplication cannot be scored right by being "close".
- **F2b — spelled integers.** Number words 0–20 are digitized in the numeric path (a count answered "three
  times" is parsed, not a fake negative).
- **F3 — token vs substring.** Whole-token / contiguous-token-run match, NEVER substring, so single-letter
  golds are safe.
- **F4 — enumerated equivalents.** Per-item `accept` list of acceptable alternative golds, frozen at
  construction (`dong` accepts `Vietnamese dong`; `Vatican City` accepts `Vatican`); digit↔word (0–20) and
  article stripping remain global.
- **F4b — diacritic/native-spelling folding.** NFKD + combining-mark stripping + a small non-decomposing map
  (`ł→l`, `đ→d`) so a correct native spelling ("Polish złoty", "Vietnamese đồng") matches the ASCII gold.
- **F5 — deduction answer token.** Numeric deduction golds route through the numeric path; yes/no and
  named-entity golds through F3.
- **F5b — single-letter entity golds (the deduction-scoring fix).** Extract the CONCLUSION letter — the
  standalone uppercase A–Z after the LAST answer marker, else the last standalone uppercase letter — and
  compare CASE-SENSITIVELY to the gold/accept letters (truncated replies excluded per F1). This turns the
  fabricated deduction ceiling (substring 22/22) into the true 0.20–0.40 rate; any run that scores deduction
  by substring/token-presence fabricates a ceiling.

---

## 5. Analysis plan

**Regression metrics** (regime a). R² and Spearman rank correlation between predicted and ground-truth log
volume on held-out in-distribution prompts. Spearman co-reported because a **floor mass point** exists in the
target (prompts whose 10 continuations are semantically identical hit the exact degenerate minimum
`10·log(1e-6) = −138.155`; the log-volume target is therefore mixed discrete-continuous at the bottom of its
range, and R² is sensitive to a mass point while Spearman is robust to it — `THRESHOLDS-PROPOSAL.md`). R²
stays the registered fidelity bar (the claim's natural scale); Spearman is required alongside it.

**OOD rotation** (regime c, load-bearing, e3-0005). Leave-one-task-family-out over all five families. The
transfer statistic is the **within-held-out-family Spearman** (rank correlation of predicted vs true volume
*inside* the held-out family — immune to between-family mean structure), pooled as the **mean over rotations**
(pinned, `ood.py`), with the **per-rotation minimum** retained for a per-family floor and a **range-coverage
flag** (a held-out family whose true-volume range is not covered by the training range is extrapolation, not
transfer). The pooled-R² statistic and the OOD/in-distribution ratio are co-reported descriptively
(exploratory). This replaces the retired `r2_ood_min` pooled-R² bar, which the audit showed satisfiable by
family recognition alone (`decisions/e3-0005-audit-redesign.md`).

**Correctness comparison** (regime b, `e3-0003`). Every comparator and the probe scored by **AUROC over the
answerable subset** (126 items with a defined correctness label), so the metric is identical across arms and
scale-independent. Pairwise differences (probe vs each baseline, **B1 first**) reported with **paired
bootstrap confidence intervals** over prompts. The correctness label feeding AUROC is whether the model's
answer is correct, scored under the frozen family-appropriate normalizer.

**Verdict branch logic** (`verdict.py`, redesigned by e3-0005, proven on planted fixtures in `VALIDATION.md`;
the module **invents no threshold**). **Eleven branches**, in decision precedence (top to bottom; the first
matching branch is the verdict):

0. **not-evaluable/correctness-arm** *(terminal precondition; neither confirmation nor refutation)* — the
   answerable subset carries fewer than `min_negatives` negatives, so the correctness arm cannot be evaluated
   at all. Checked **before** any branch (`preconditions.py`).

Then, if **continuous fidelity holds** — all four of: R²_nondeg ≥ `r2_fidelity_min`, Spearman_nondeg ≥
`spearman_fidelity_min`, within-family Spearman ≥ `within_family_spearman_min`, family-oracle margin
(probe R² − family-mean-oracle R²) ≥ `family_oracle_margin_min`, all on the **non-degenerate subset**:

1. **refuted/length-confounded** — (`require_length_robust`) the length-residualized within-family Spearman
   falls below `within_family_spearman_min`: the fidelity was a continuation-length readout.
2. **refuted/ood-range-uncovered** — any rotation's held-out true-volume range is not covered by training:
   extrapolation, not transfer.
3. **refuted/ood-failure** — pooled within-held-out-family Spearman < `ood_pooled_spearman_min` OR any
   per-rotation Spearman < `ood_per_family_floor`: the shortcut/collapse the OOD regime catches. *(OOD is
   resolved BEFORE the added-value gates.)*
4. **refuted/no-margin-over-verbalized** — probe does not beat the max over verbalized variants
   (`probe_vs_vc_ci_low ≤ vc_ci_floor`).
5. **refuted/no-margin-over-entropy** — probe does not beat predictive entropy B3
   (`probe_vs_b3_ci_low ≤ b3_ci_floor`).
6. **refuted/dominated-by-correctness-probe** — B4 dominates the probe
   (`b4_vs_probe_ci_low > b4_margin_ceiling`).
7. **confirmed-shaped** — fidelity, length-robustness, OOD transfer, and all three added-value gates clear.

Else (**no continuous fidelity**):

8. **refuted/binary-only** — median-split AUROC ≥ `auc_binary_min`: signal exists only at binary granularity
   (already known from SEP).
9. **refuted/margin-only** — above the R² floor (R²_nondeg ≥ `r2_fidelity_min`) but denied by the
   margin/within-family gates with no binarized signal — the row the pre-redesign code mislabeled
   `refuted/no-signal`.
10. **refuted/no-signal** — no fidelity, no binarized signal.

The three distinct added-value branches (4/5/6) and the length branch (1) are a deliberate choice to name
each honest failure separately rather than conflate them; flagged as a spec interpretation in `VALIDATION.md`
(reversible in one line if the registration prefers a collapsed label). These branches implement the README
verdict conditions as refined by e3-0005, and every branch was routed correctly on planted fixtures
(`VALIDATION.md`: linear-transfers → confirmed-shaped; no-signal control → refuted/no-signal; binary-only →
refuted/binary-only via a **−0.186** class-mean margin; family-band-only fixture → refuted, never confirmed;
degenerate-mixed → two-part recovery; length-confound → refuted/length-confounded; correctness-arm bundle →
added-value gates). **99 tests pass**, CPU-only, no model, no network. The fixture routing thresholds
(`_fixtures.py`) are throwaway and carry no scientific commitment.

**The verdict is a function of EXACTLY these quantities and no others** (`VerdictInputs`; the audit's
"~8 quantities" clause, D24): `n_negatives`; `r2_nondegenerate`, `spearman_nondegenerate`
(+ `n_nondegenerate`, `n_degenerate`, `degeneracy_auroc` reported); `within_family_spearman`,
`within_family_r2`, `family_oracle_r2`, `family_oracle_margin`; `within_family_spearman_length_resid`;
`r2_indist`, `r2_classmean_indist`, `auc_binary`; `ood_pooled_spearman`, `ood_min_rotation_spearman`,
`ood_range_uncovered`; `probe_vs_vc_ci_low`, `probe_vs_b3_ci_low`, `b4_vs_probe_ci_low`. No other measured
quantity enters the decision; `classmean_margin` (= `r2_indist − r2_classmean_indist`) is computed and
reported but is **not** a gate.

**Thresholds table — PROPOSED, to be confirmed by the registrant** (`THRESHOLDS-PROPOSAL.md`; every value
below binds nothing until the registrant fixes it at registration; the gating names match `VerdictThresholds`
exactly, with `correctness_cv_folds`, the alpha grid, CV folds, and bootstrap n/CI being module-level params
of `correctness.py`/`probe.py`/`compare.py`):

| parameter | proposed | sweep band | basis (condensed) |
|---|---|---|---|
| `min_negatives` | **15** | {15, 20} | Precondition: below this the correctness arm is not-evaluable, not refuted. Rehearsal fired confirmed on **1** negative; calibration projects ~25–32 negatives at 126 answerable. Rehearsal-informed (its own note said ≥ 20 — the stricter sweep point). |
| `r2_fidelity_min` | **0.10** | {0.05, 0.10, 0.20} | No external anchor (field uses binarized AUROC). Scored on the non-degenerate subset; modest — the Spearman/within-family/oracle gates are the real discriminators. |
| `spearman_fidelity_min` | **0.3** | {0.2, 0.3, 0.4} | Floor-mass-robust half of the two-part target; Spearman is immune to the `N·log(ε)` mass point R² is sensitive to. |
| `within_family_spearman_min` | **0.3** | {0.2, 0.3, 0.4} | Kills the family-band confound (rehearsal η² = 0.255) and is the bar the length-residualized Spearman must also clear. (Instrument fixture used 0.5 only to route planted cases — not a proposal.) |
| `family_oracle_margin_min` | **0.05** | {0.05, 0.10} | Probe must beat the family-mean oracle; replaces the class-mean margin as the gate. |
| `r2_margin_over_classmean_min` | **0.05** *(reporting only)* | — | Demoted: B2 reporting quantity, no longer a fidelity gate. |
| `ood_pooled_spearman_min` | **0.2** | {0.2, 0.3} | Pooled within-held-out-family Spearman transfer bar; immune to between-family means (rehearsal pooled 0.667). |
| `ood_per_family_floor` | **0.0** | {0.0, 0.1} | No rotation may collapse; catches the rehearsal's near-zero `factual` rotation (+0.060). |
| `auc_binary_min` | **0.70** | — | Bottom of SEP's 0.7–0.95 range; distinguishes binary-only/margin-only from no-signal; gates no confirmation. |
| `vc_ci_floor` | **0.0** | — | Strict beat of the **max** verbalized variant (CI-low of probe's margin over the strongest B1 > 0). |
| `b3_ci_floor` | **0.0** | — | Strict beat of predictive entropy B3 (added because B3 is free and pilot ρ(vol, entropy) = 0.827). |
| `b4_margin_ceiling` | **0.0** | — | B4 must not dominate ((B4 − probe) CI-low ≤ 0); anchored in arXiv:2509.10625 (B4 beats VC on Qwen2.5-7B). |
| `require_length_robust` | **true** | — | Enforce the length gate; mandatory given rehearsal ρ(vol, mean length) = 0.910. |
| `correctness_cv_folds` | **5** | {5, 10} | Out-of-fold folds for OOF probe/B4 correctness scoring (no in-sample path). |
| ridge `alpha` grid | **logspace(10⁻², 10⁶, 9)** | — | Decade grid at d=3584, n≈200; inner 5-fold CV on train only. |
| inner CV folds | **5** | — | Convention; n≈160 train → ~32/fold. |
| bootstrap resamples | **10,000** | — | Stable 95% CI tails at ~126; cheap. |
| CI level | **95% two-sided** | — | Program convention (α = 0.05). |

**How the sweeps work — pre-registered, not post-hoc** (`THRESHOLDS-PROPOSAL.md`). The registered value of
each swept parameter is the **primary**; the verdict is computed at the primary. Sweep values are computed
and reported alongside, and the write-up states whether the verdict branch is stable across the sweep. A
verdict that flips inside its sweep band is reported as **threshold-fragile** — a pre-registered honesty
label, not a re-decision. **No sweep value may be promoted to primary after data exists** — that requires a
new registration (`e3-0004` freeze boundary).

---

## 6. Pilot-testing disclosure (`experiments/README.md` § Run discipline #4)

E3's instrument was exercised before this registration on **four** disposable stages — spike (20), pilot
(30), labeled dress rehearsal (41), and kind-based hardening calibration (102), **193 disposable prompts in
total**, all enumerated in `corpus/DISPOSABLE-MANIFEST.jsonl` and all disjoint from the corpus. Every stage
is disclosed here in full, and **no number from any of them is evidence for or against H-VOL.**

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

**Labeled dress rehearsal (`REHEARSAL.md`, `rehearsal/`) — 41 throwaway prompts (disjoint).** The **entire**
analysis path — probe fit, splits, AUROCs, paired bootstrap, verdict branch — run on labeled disposable data,
every step calling `e3_validation`. It is the stage that **forced the audit-driven redesign**: it fired
`confirmed-shaped` off a correctness arm with **one** negative (a truncation artifact; genuine error rate
0/41), measured ρ(volume, mean length) = 0.910 (rank) and between-family η² = 0.255, and measured the
target's split-half reliability (Spearman-Brown 0.965 — above every proposed R² bar, so target noise is not
the binding constraint). Every frozen choice traceable to it (the `min_negatives` precondition, the length
gate, the two-part fidelity target, the within-family/OOD-Spearman gates, the B3 gate) is disclosed as
rehearsal-informed. No number is a result about H-VOL.

**Kind-based hardening calibration (`hardening/HARDENING.md`) — 102 throwaway prompts (3 rounds, disjoint).**
Per-kind greedy-accuracy search for hard *kinds* (the rehearsal proved degree-hardening buys ~zero
negatives). Selected the three d4 kinds (`arith_mult3x3` 0.125, `fact_numeric_tail` ≈ 0.55–0.79, `ded_seat6`
0.20–0.40), the improved-normalizer F1–F5b spec, and the ≥ 768-token answer-cap recommendation. No hidden
state, volume, or probe was computed; no number is a result about H-VOL.

**Iterations and contamination.** No prompt/hypothesis iteration shaped the *hypothesis* — H-VOL predates the
instrument work. The threshold *values* are pilot/rehearsal/calibration-informed as disclosed above and
remain open until the registrant fixes them. All four throwaway sets (20 spike + 30 pilot + 41 rehearsal +
102 calibration = 193) are marked THROWAWAY, are mutually disjoint, and **must never appear in or seed the
corpus** — the same anti-contamination ordering as E0 PLAN step 4 and the harness synthetic-fixtures rule.
`corpus/assemble_verify.py` (calling `corpus/decontaminate.py` against `DISPOSABLE-MANIFEST.jsonl`) checks and
enforces zero overlap; six pilot/calibration-overlapping ids were found and replaced in place (§ 2).

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
- **Closest prior art — BbZKxrZCNn** (Semantic Entropy Probes authors, NeurIPS 2024 MINT workshop; accessed
  via the Internet Archive Wayback Machine in the second-round read, `PREFLIGHT.md`). Trains a LASSO
  **regression** on **continuous semantic entropy** from hidden states — so "continuous uncertainty
  regression target from a hidden state" is **not novel in itself**. It is **in-distribution only, uses no
  volume, runs no OOD transfer test, and no head-to-head against verbalized confidence or a correctness
  probe.** E3's edge is defined strictly against it: a **volume** target (a different quantity than semantic
  entropy, extending to open-ended tasks where entropy clustering fails), a **leave-one-family-out transfer**
  test, and a **B4/B3/verbalized head-to-head** — none of which BbZKxrZCNn has.
- **Why the volume/transfer question is sharp — correctness directions provably do not transfer.**
  arXiv:2506.08572 (verified full text): correctness directions in the hidden state are near-orthogonal
  across tasks, isolated on math, and mixtures do not fix it. arXiv:2509.10625 (verified full text): a
  correctness probe (B4) beats verbalized confidence on Qwen2.5-7B and correctness directions fail on math.
  E3 asks whether a **volume** direction transfers where these correctness directions demonstrably do not.
- **What does not exist** (verified absent): a probe with the **continuous volume** as regression target
  tested for **cross-family transfer** and in **head-to-head** against B4, B3, and verbalized confidence. Any
  bridge from belief-state geometry (Shai et al., arXiv:2405.15943) to LLM-scale uncertainty is **labeled
  speculation**, not a claimed edge.

**The claimed edge, stated narrowly** (`e3-0003`, `PREFLIGHT.md` § second round): **not** "first continuous
uncertainty regression from a hidden state" (BbZKxrZCNn did that for semantic entropy, in-distribution),
**not** "first to compare verbalized confidence against a cheaper signal" (that space is active —
arXiv:2505.23845, 2604.24070, 2502.06233, 2510.04108), **but** the **first test of whether a continuous
*volume* direction transfers across task families where correctness directions provably do not, and whether
it adds value over a correctness probe (B4), predictive entropy (B3), and zero-shot verbalized confidence.**

- **arXiv:2503.14749 — version-anchored.** v1 is SFT-only (teaching a model to *verbalize* calibrated
  confidence — no probe, no head-to-head); **v2/v3 add a P(IK) probe baseline vs verbalized confidence**
  (their tables report the verbalized method beating P(IK)). It **does not preempt** E3 but is cited both as
  a **stronger conceivable B1** and, at v2/v3, as adjacent probe-vs-verbalized prior art. The version is
  anchored because the claim differs across versions; a reviewer objection that an SFT-strengthened verbalized
  arm might beat the probe is **legitimate and acknowledged** (E3 freezes the strongest *simple* zero-shot
  arm and cites the stronger conceivable one).
- **Format-confound control adopted — arXiv:2606.02907.** Its residualization protocol (regress format
  features — family ID, prompt/answer length, option structure — out of the hidden states and re-probe) is
  **adopted as a registered control**; fidelity surviving residualization is stronger evidence than
  leave-one-family-out alone. This is the source of the length-residualized gate (§ 5).
- **4-bit host scoped, not apologized for — NF4 (arXiv:2606.02628).** 4-bit (NF4) probing of Qwen2.5-7B is a
  **published precedent** that works; it **corrects** the pre-mortem's false "no cited probe paper used a
  quantized host" (`PREMORTEM.md` § 8). E3's scope line is "linear readability in the 4-bit-quantized
  deployment form" — arguably the more deployment-relevant claim; an fp16 replication is a hardware-permitting
  follow-up.

**Citation ceiling / primary-source gate.** Prior-art claims here are `abstract-checked`, then **full-text
read by the second-round automated review pass** (`PREFLIGHT.md`) — but **not `verified`** until a named
person reads the primary source (E0 PLAN § Guards). **The run remains gated on primary-source verification by
a named reader** of arXiv:2406.15927 (binarized-target — now quoted verbatim in the second-round read: the
SEP target is the binarized best-split threshold, no continuous variant), BbZKxrZCNn (continuous SE
regression — Wayback-accessed; the retrieved PDF is retained **outside** the repository, not committed), and
arXiv:2503.14749 (version-anchored). Per-citation statuses: `VERIFICATION.md`.

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

**Gate order (e3-0005; ledger D25).** The human gates below are ordered: **thresholds are fixed no later than
corpus approval** (a threshold set after the corpus is seen is post-hoc); corpus approval precedes the OSF
submission; the OSF timestamp precedes the explicit human go for the confirmatory run. Each gate is a
separate human act; none proceeds on automation.

1. **Threshold confirmation.** Every value in the § 5 table is `PROPOSED` (`THRESHOLDS-PROPOSAL.md` binds
   nothing), including the ten e3-0005 additions. The registrant fixes each primary value and each sweep band
   at registration, **no later than corpus approval**. Once data exists, no sweep value may be promoted to
   primary without a new registration.
2. **Corpus approval.** `corpus/candidates.jsonl` (200 prompts) is a **proposal**. The registrant must
   approve (1) these 200 as the confirmatory set, (2) the five-family partition as the OOD rotation, (3)
   golds/covariates frozen at construction — before any hidden state or continuation exists. Approval does
   not unfreeze `e3-0001`–`e3-0005` and does not itself authorize a run.
3. **Primary-source citation verification.** The run is gated on a **named reader** verifying the primary
   sources of: **arXiv:2406.15927** (Semantic Entropy Probes — binarized-target; the second-round read quoted
   the binarized best-split target verbatim, but a named human read is still required to flip the ledger
   status); **BbZKxrZCNn** (the closest prior art — continuous SE regression; read at full text via Wayback
   in the second round, the retrieved PDF retained outside the repo — a named human read moves it from the
   automated-read to the verified list); **arXiv:2503.14749** (version-anchored stronger-B1 / v2-v3 P(IK)
   citation); and the second-round full-text findings **arXiv:2506.08572**, **arXiv:2509.10625**,
   **arXiv:2606.02907**, **arXiv:2606.02628 (NF4)**. All are `full-text-read-by-automation`, **not** yet
   `verified` (citation ceiling). Update `VERIFICATION.md` on discharge.
4. **OSF submission itself.** Creating the OSF registration and obtaining its external timestamp is the
   human-only preregistration act (`METHODOLOGY.md` nonconformance №1: git self-timestamps do not count;
   OSF/Zenodo do). Its timestamp must predate the first confirmatory datum.
5. **Explicit human go for the confirmatory run.** Beyond `0006`'s rule, `e3-0004` requires an explicit human
   go for the confirmatory run — the synthetic-validation stage and the primary-source checks gate it, and no
   confirmatory datum is generated on automation alone. Registration, corpus approval, and the run are each
   separately human-gated.
6. **Decision-record status transition.** All of `e3-0001`–`e3-0005` (and program `0006`) are `proposed`.
   Their `proposed → accepted` transition and the merge-time renumbering of the `e3-*` records into the
   global `decisions/` sequence are registrant/merge acts, not part of this draft.
7. **HYPOTHESES.md § H-VOL kill-condition amendment.** The kill condition aligned to the redesigned contract
   (adds B3/B4/not-evaluable/family-band/length clauses) is proposed in `decisions/e3-0005-audit-redesign.md`
   and applied at **merge time** — HYPOTHESES.md is frozen on this branch and is not edited here.

---

## 10. Commitment statement

- **No confirmatory datum exists at the time of this draft.** No real hidden state, continuation, embedding,
  volume, correctness label, or verdict has been generated for the E3 corpus. The only numbers produced so
  far are from the **four disposable stages — spike (20) + pilot (30) + labeled dress rehearsal (41) +
  hardening calibration (102) = 193 throwaway prompts** (`corpus/DISPOSABLE-MANIFEST.jsonl`), all disposable,
  all disjoint from the corpus, **none evidence about H-VOL** — including the rehearsal's `confirmed-shaped`
  branch, which is a plumbing observation about the decision logic (it is what forced the e3-0005 redesign),
  not a scientific outcome. The whole value of this registration is that it is fixed and externally
  time-attested **before** the first confirmatory datum exists.
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
