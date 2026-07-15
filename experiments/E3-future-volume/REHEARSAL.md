# E3 labeled dress rehearsal — the full analysis path on 41 labeled throwaway prompts

**The rehearsal answers one question the pilot could not: run the ENTIRE analysis path — probe fit,
splits, AUROCs, paired bootstrap, verdict branch — on labeled disposable data, and eyeball every
number for "would this embarrass us at 200 prompts." The answer: two numbers would. Negatives = 1
of 41, and that one negative is a truncation artifact, not a wrong answer — the model's genuine
error count on this set is ZERO, including on the difficulty band the corpus hardening was going to
add. Every correctness AUROC below, the paired-bootstrap CI, and the verdict branch that fired are
functions of a single mislabeled prompt.**

Everything here is DESCRIPTIVE at n = 41 disposable prompts. Nothing is a result about H-VOL; no
number below licenses any confirmatory claim. Code and raw records: `rehearsal/run_rehearsal.py`
(prompts, pipeline), `rehearsal/normalizer.py` (correctness scoring), `rehearsal/analyze_rehearsal.py`
(the full stats path — every step CALLS `e3_validation`, nothing reimplemented),
`rehearsal/disjointness.py`, `rehearsal/results/` (per-prompt JSON + npz, `analysis.json`,
`disjointness.json`, `run_config.json`).

## What ran

41 fresh throwaway prompts, hardcoded and marked THROWAWAY, spanning the three ANSWERABLE corpus
families (`arithmetic` 13, `factual` 14, `deduction` 14), each with an author-verified unambiguous
gold and an intended difficulty 1–4:

- **d1 (10 items)** — trivial, corpus-difficulty-1-like (9×8; capital of Italy; one-step syllogism).
- **d2 (10 items)** — medium, corpus-difficulty-3-like (40% of 250; symbol for oxygen; 3-step chain).
- **d3 (11 items)** — hard (multi-step word problems with unit handling; capital of Australia;
  4-entity orderings with a distractor relation).
- **d4 (10 items)** — very hard but still single-answer — **the band the planned corpus hardening
  would add** (3-for-$2 unit-price problems, two-stage tank fills, age equations; symbol for
  tungsten, smallest country; 5-entity middles, elimination puzzles, chained age deduction).

Golds verified at construction: arithmetic recomputed from scratch; factual single-canonical;
deduction re-derived from premises. Per prompt, the pipeline is the decision-record pipeline
exactly as the pilot wired it (`pilot/run_pilot.py` pattern, pins identical, base_seed 20260714):

1. **e3-0001 extraction + e3-0003 B3** — one forward pass, no generation; hidden state
   `model.model(ids)[:, -1, :]` (3584-d, fp16→fp32); predictive entropy from the same pass.
2. **e3-0002 ground truth** — N = 10 seeded continuations, temp 0.7 / top-p 0.95, 256-token cap,
   early EOS kept; seed = base_seed + prompt_index·10 + draw_index.
3. **Embedding + volume** — nomic-embed-text-v1.5 (revision `e9b6763023c676ca8431644204f50c2b100d9aab`,
   dim 768, `clustering: ` prefix), volume by calling `e3_validation.volume.semantic_volume`.
4. **e3-0003 B1** — two-turn verbalized confidence, frozen verbatim elicitation, greedy,
   first-int-0-100 parse, one retry.
5. **NEW: one dedicated greedy answer** (temp 0) per prompt, scored against the gold by the
   family-appropriate normalizer (below) — separate from the 10 sampled continuations.

Derived seeds, all off base_seed = 20260714: continuation draws as above; analysis seeds
split = base+1, paired bootstrap = base+2, single-arm CI = base+3, synthetic mixtures = base+4.

Run health: 41/41 prompts completed, 0 exclusions (every prompt yielded 10 valid continuations),
0 verbalized-confidence parse failures (values were only ever 95 or 100), total pipeline wall
26.4 min. 11/41 prompts sit on the exact degenerate volume floor 10·log(1e-6) = −138.155; volume
range −138.155 to −15.383.

## Disjointness (grep-checked, `rehearsal/results/disjointness.json`)

Zero exact overlaps against all three reference sets. Max token-set (Jaccard) similarity:

| reference | exact overlaps | max Jaccard | argmax pair |
|---|---|---|---|
| spike-20 | 0 | 0.750 | "chemical symbol for oxygen?" vs "…for gold?" |
| pilot-30 | 0 | 0.750 | "chemical symbol for oxygen?" vs "…for sodium?" |
| corpus-200 | 0 | 0.800 | "What is 9 times 8?" vs "What is 9 times 9?" |

All three maxima are the short-question-frame effect (function words dominate the token set of a
five-word prompt); every pair differs in content and gold. One genuine near-duplicate WAS caught
by this check during construction — a deduction item that reused a corpus item's exact
Red/Blue/Green/Yellow weight scenario with only the question flipped (Jaccard 0.833) — and was
replaced with a fresh density scenario before that prompt ever ran. The check earned its keep.

## Correctness normalizer — implementation and vagueness findings

`normalizer.py` implements CORPUS.md § Labeling protocol concretely: arithmetic = extract the
final number, compare numerically; factual = case/article-insensitive whole-token match with
digit↔word equivalence for 0–20; deduction = normalized whole-token match of the answer token,
numeric golds routed through the numeric path. 12/12 on its construction self-check.

Places where the spec was too vague to implement without inventing a rule (each invented rule is a
finding, not a decision — the frozen config must pin these):

- **V1 — "extract the final number" is undefined under truncation and restatement.** Implemented
  as the last numeric literal in the reply. This mislabeled prompt 12 (below): the model's answer
  was cut by the 256-token cap mid-derivation, so the "final number" was an intermediate (the
  rectangle's length, 12), not the answer (72). The spec never says what to do when the final
  answer was never emitted.
- **V2 — no numeric tolerance rule.** `30`/`30.0`/`$30` match by construction; a legitimately
  rounded answer ("about 33" for 100/3) has no rule and scores wrong. Not hit in this run;
  will be hit at corpus scale in rate/percentage items.
- **V3 — "match" is not defined as token vs substring, and single-letter golds make the
  difference load-bearing.** Substring matching would score the letter "o" as present in almost
  any sentence. Implemented as whole-token (contiguous token-run for multi-word golds). The real
  corpus dodged this by removing chemical-symbol items; the rehearsal kept O/C/K/W golds
  deliberately and whole-token matching scored all of them correctly.
- **V4 — "obvious equivalents" is not enumerable.** Implemented: digit↔word 0–20, articles
  stripped. "The Vatican" vs gold "Vatican City" would NOT match under this rule; the model
  answered "Vatican City" verbatim, so the hazard did not fire here — but it exists.
- **V5 — deduction "answer token" collides with V3 for single-letter entities** (switch "C");
  same whole-token resolution, worked (gold C, got "c").

## The full stats path (every number DESCRIPTIVE at n = 41, labeled as such)

Fit and scored by CALLING the instrument: `splits.in_distribution_split` (test fraction 0.30,
seed base+1), `probe.ridge_probe` (e3-0001 recipe: train-only z-score, inner 5-fold CV alpha over
the THRESHOLDS-PROPOSAL grid logspace(10⁻², 10⁶, 9)), `probe.logistic_median_split_probe`,
`probe.class_mean_predictor_r2`, `splits.leave_one_family_out`, `compare.auroc`,
`compare.paired_bootstrap_auroc_diff` (10k, 95%), `verdict.decide` at the proposed thresholds.

| quantity | value | note |
|---|---|---|
| in-dist ridge R² (train 29 / test 12, α=10) | **+0.743** | descriptive at n=41, NOT a result |
| in-dist Spearman | +0.819 | |
| class-mean predictor R² | +0.340 | margin over class-mean = +0.404 |
| SEP median-split logistic AUROC (volume class) | 0.944 | 12-item test split |
| leave-one-family-out pooled R² | **+0.454** | pooled over all 41 held-out predictions |
| LOFO pooled Spearman | +0.667 | |
| LOFO per-family R² | arith +0.429 / deduction +0.329 / factual +0.060 | factual barely transfers |
| **volume target split-half reliability** | Pearson 0.933 (draws 0-4 vs 5-9), Spearman 0.862, Spearman-Brown full-length **0.965** | the target-reliability ceiling no record had measured; N=5 halves understate N=10 reliability |

### Correctness AUROCs (over all 41; direction fixed so higher score ⇒ predicted-correct)

**Read the negatives row first — it invalidates this whole block.** Negatives = 1 of 41, and that
single "incorrect" label is the V1×cap truncation artifact on prompt 12 (arithmetic d3, perimeter→
area: greedy answer hit the 256 cap after deriving L=12 and before multiplying by 6). AUROC with
one negative is the rank of one score among 40 — a coin with a memory, not a metric.

| arm | AUROC | basis |
|---|---|---|
| probe (LOFO held-out predicted volume, negated) | 0.825 | 1 negative |
| ground-truth volume (negated; descriptive ceiling) | 0.875 | 1 negative |
| binarized probe (LOFO median-split decision score) | 0.725 | 1 negative |
| verbalized confidence (B1) | 0.475 | 1 negative; VC took only two values, 95 and 100 |
| predictive entropy (B3, negated) | 0.600 | 1 negative |

Paired bootstrap probe-vs-VC (10k resamples, 95%, seed base+2): diff = **+0.350**,
CI = **[+0.218, +0.474]**, excludes zero. **This CI is fake precision**: every replicate's AUROC
is determined by where the single negative's scores land; resampling 41 items cannot manufacture
information that one label carries.

### Verdict at the THRESHOLDS-PROPOSAL values

`verdict.decide` fired **confirmed-shaped** (r2_indist 0.743 ≥ 0.10; margin 0.404 ≥ 0.05;
r2_ood 0.454 ≥ 0.05; probe-vs-VC CI-low 0.218 > 0.0). That the pipeline cheerfully produced its
strongest branch from an AUROC clause resting on one mislabeled prompt is the single most
important output of this rehearsal: **the verdict logic has no guard on the evidential mass of
the correctness labels.** A minimum-negatives precondition (or a minimum class count for the
AUROC clauses) does not exist anywhere in the records, and this run proves it can fire without one.

## Calibration (the decision-feeding numbers)

Accuracy by intended difficulty — the curve the corpus hardening was to be set from:

| difficulty | n | correct | accuracy |
|---|---|---|---|
| d1 (trivial, corpus-d1-like) | 10 | 10 | 1.000 |
| d2 (medium, corpus-d3-like) | 10 | 10 | 1.000 |
| d3 (hard) | 11 | 10 | 0.909 (the one miss is the truncation artifact) |
| d4 (very hard — the hardening band) | 10 | 10 | 1.000 |

By family: arithmetic 12/13 (0.923; artifact), factual 14/14, deduction 14/14. Greedy answers
truncated by the 256 cap: 1 (prompt 12), and that one is the "negative."

**The curve is flat at 1.0.** Qwen2.5-7B-Instruct at greedy does not break anywhere in this band —
not on two-stage percentage word problems, not on 5-entity orderings, not on tungsten/Ottawa/
Vatican-City retrieval. The difficulty knob the corpus anchors describe (and the harder band this
rehearsal added on top) does not produce negatives on this model.

AUROC CI width at n = 41, observed negative rate 0.024 (single-arm percentile bootstrap, 10k):
probe 0.825 CI [0.700, 0.925] width 0.225; gt-volume 0.875 CI [0.769, 0.974] width 0.205 — and
both widths are themselves untrustworthy for the same one-negative reason.

Extrapolated AUROC CI width at n = 126 (the answerable-subset size) — synthetic-mixture bootstrap:
class-conditional score distributions resampled from the rehearsal's observed scores to the target
n and negative rate, 2000 reps, 95% two-sided. **Method caveat that swallows the method: the
"incorrect" score pool has exactly one member**, so the negative side of every mixture is one
value resampled; these widths are optimistic lower bounds:

| negative rate | probe CI width | gt-volume CI width |
|---|---|---|
| 10% (13 of 126) | 0.142 | 0.115 |
| 25% (32 of 126) | 0.149 | 0.128 |
| 40% (50 of 126) | 0.171 | 0.145 |

Even at face value: a ±0.07 AUROC interval at 126 items is wide against literature deltas
(SEP-replication 0.62–0.80 spans 0.18). Reading: the corpus needs BOTH a real negative rate
(≥ 25% preferred) AND for the probe-vs-VC margin to be large (≥ 0.10) before a 95% CI can be
expected to exclude zero at n = 126.

## Confound numbers (descriptive; feed the interpretability audit)

| pair | Pearson | Spearman |
|---|---|---|
| volume vs mean continuation length | +0.786 | **+0.910** |
| volume vs std continuation length | +0.660 | +0.711 |
| volume vs predictive entropy (B3) | +0.337 | +0.627 |

Volume variance decomposition over the three families: between-family η² = **0.255**, within-family
= 0.745. Most volume variation lives inside families, which is what the within-family difficulty
spread was designed to produce — but see the length line: at Spearman +0.910, **the volume statistic
is nearly rank-identical to mean continuation length on this set.** A probe that reads "how long
will the reply be" from the hidden state would reproduce most of the volume ranking without reading
any semantic-dispersion geometry. The interpretability audit needs a length-partialled analysis
(volume residualized on length, or length as a registered covariate) before any probe R² is
interpreted as geometric.

## Disclosure block

- **All 41 rehearsal prompts are disposable.** They are marked THROWAWAY in
  `rehearsal/run_rehearsal.py`, are disjoint from the spike-20, the pilot-30, and the corpus-200
  (checked, table above), and MUST NEVER appear in, or seed, the real E3 corpus.
- **No number here is evidence for or against H-VOL.** n = 41 throwaway items; the verdict branch
  reported above is a plumbing observation about the decision logic, not a scientific outcome.
- **This rehearsal informs the corpus hardening and the threshold proposal** (difficulty
  calibration, negative-rate requirement, normalizer pinning, cap handling, minimum-negatives
  guard). Per the program's pilot-testing discipline, **that it did so is itself disclosed: the
  registration must list this rehearsal alongside the spike and pilot as pilot material**, and any
  frozen choice traceable to a rehearsal observation is disclosed as rehearsal-informed.

## Lines that would embarrass us at scale

Honest reading of every number that looks fragile, worst first:

1. **"Negatives: 1" — and the 1 is a labeling artifact.** The genuine error count is 0/41 across
   trivial-through-very-hard single-answer prompts. If the confirmatory corpus's difficulty
   resembles its own anchors, the answerable-subset AUROC comparison — the entire e3-0003
   correctness arm, the probe-vs-VC margin, the no-margin-over-verbalized branch — is arithmetic
   on a handful of accidental labels. This was empirically discoverable for the cost of 26
   minutes of compute, and it was.
2. **The hardening band does not harden.** d4 accuracy = 1.000. Multi-step arithmetic word
   problems, 4+-constraint deductions, and less-common single-answer facts — the exact classes
   the corpus hardening planned to add — do not move Qwen2.5-7B off ceiling. Hardening has to
   change kind, not degree: genuinely adversarial arithmetic (larger operands, awkward fractions),
   confusable near-miss facts, deductions with premise interference — and then be re-measured on
   a fresh disposable set before the corpus is frozen, because this curve says the current plan
   buys ~zero negatives.
3. **`verdict.decide` fired its strongest branch on evidentially empty AUROC.** No clause checks
   that the correctness labels carry mass (minimum negatives / minimum class count). At 126
   answerable items with a 2–5% negative rate, the real run could "confirm" or "refute" the
   verbalized-margin clause on 3–6 labels. The registration should add a pre-registered
   precondition (e.g. ≥ 20 negatives or the AUROC clauses are reported as not-evaluable).
4. **Volume ≈ length (Spearman +0.910).** The headline continuous target is close to a
   continuation-length readout on this set. Without a registered length-control analysis, a
   confirmed-shaped verdict at scale would be one "your probe reads verbosity" review away from
   collapse.
5. **The 256-token cap poisons correctness labels.** One of 41 greedy answers truncated
   mid-derivation and became the run's only "negative." Corpus arithmetic d3 items induce long
   chain-of-thought; at scale this is a systematic mislabeling channel biased exactly against the
   hardest answerable items. The frozen config needs either a larger answer cap, a final-answer
   elicitation format, or a truncation-flagged exclusion rule for correctness labels — decided
   and pinned before the run.
6. **Verbalized confidence has almost no support: every value was 95 or 100.** Its AUROC (here
   0.475) is decided by which side of a two-point scale the few negatives land on. "Probe beats
   VC" may be won or lost by discreteness noise, not by information — an argument for co-reporting
   a margin against B3 entropy as well, which at least varies.
7. **The n = 126 extrapolation rests on a one-member negative pool.** The CI-width table above is
   the best available from this data and still close to worthless; treat it as a floor, not an
   estimate.

Smaller notes for completeness: LOFO transfer to `factual` was near-zero (+0.060) — with only
three families in the rehearsal, one weak rotation dominates the pooled OOD number; 11/41 volumes
sit on the exact degenerate floor, so the mass point the pilot found in open families is present
even in answerable-only sets; the in-dist R² of +0.743 at n=41 with d=3584 should be read as
near-meaningless — 12 test points against a 3584-dim ridge.

What did NOT embarrass: the target itself is reliable (split-half 0.933, Spearman-Brown 0.965 —
comfortably above every proposed R² bar, so target noise is not the binding constraint); the
instrument ran end-to-end with zero exclusions, zero parse failures, zero crashes; the disjointness
check caught a real near-duplicate at construction time; and the degenerate floor observed equals
the fixture-proven minimum exactly, again.
