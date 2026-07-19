# X-HUMAN — Human judge-validation of the contamination instruments

**Status:** authored protocol + annotation-packet spec. **No labels in this document are human labels.**
Human annotation is performed by Vlad or recruited annotators against the packets this protocol
specifies; this file authors the sampling plan, the rubric, the κ/FP/FN computation, and the
decision rules — it does not, and must not, contain fabricated adjudications.

## 0. Why this gate exists (the load-bearing problem)

Every numeric verdict in the E5/E8 line is produced by a machine contamination detector, and we now
hold **two detectors that disagree by two orders of magnitude on the same items**:

- **NLI-original** (the frozen E5/E8 instrument, `outcomes._still_asserts`: bidirectional
  DeBERTa-v3-large-MNLI, max-over-premises, threshold 0.7, whole-sentence). On A3 must_change it flags
  **200/756 (26.5%)** contaminated. This is the number the registered E8 verdict was computed from
  (`verdict-numbers.json`: A3 rates 26.7/29.4/24.1%).
- **instrument-v2** (the X1 claim-grounded value/verdict discriminator, `x1-anatomy/instrument_v2.py`).
  On the identical 756 items it verifies **1 machine-TRUE, hand-resolved to 0**
  (`x1-anatomy/X1-FINDINGS.md §0`) — it reclassifies 199/200 as `false_positive_instrument`.

The entire post-E8 conclusion — *"the operator line has no opening in A3; the first deliverable is an
instrument fix, not a model operator"* (X1-FINDINGS.md §7) — rests on **instrument-v2 being right and
NLI-original being wrong**. That adjudication is currently made by machine plus a 30-item convenience
sample read by two Sonnet agents and the lead (X1-FINDINGS.md §5), with **no chance-corrected
agreement statistic, no prevalence-stratified sampling, and no FP/FN accounting at the decision
threshold**. Under the confirmed judge-validation standards (below), that is not validation. X-HUMAN
supplies the missing layer: a stratified human panel whose labels are the ground truth against which
**both** instruments are scored, so the choice between them stops being a machine grading a machine.

Scope of what X-HUMAN validates: the A3 contamination instrument (both versions), the A3 completeness
(must_persist) instrument, and — as a second, independent regime — the E5 registered contamination
labels on which the *"release operator lost"* verdict (Arm C 11/107 vs Arm B 1/107) depends. It does
**not** re-run any model or change any frozen scoring path; it grades existing banked outputs.

## 1. The confirmed standards this protocol mirrors (do not invent past these)

Sourced from the lit sweep; mirrored, not extended.

1. **Stratified sampling by label prevalence.** Balanced binary criteria: a ~50-item baseline per
   validated criterion. Rare categories (≈6% prevalence): **200+** items to estimate the rare-class
   rate with usable precision. **Our real contamination is RARE** — instrument-v2 puts the true-echo
   prevalence at ≤0.13% and the disputed-artifact class is the majority of flags — so the class whose
   rate we must pin (genuine stale-value assertion) is deep in the **200+ regime**. We size for it
   explicitly in §3 rather than accepting a 50-item balanced baseline that would place the CI on the
   rare rate wider than the rate itself.
2. **2–3 annotators per item, Cohen's κ gate.** κ > 0.6 acceptable, κ > 0.8 strong. Every validated
   dimension carries its own κ; an item scored by <2 independent annotators contributes no κ.
3. **Per-dimension / per-item-type reporting, never pooled.** Report κ and error rates separately for
   contamination vs completeness, and separately per family type (F1 boolean-verdict / F2
   multi-requirement-threshold / F3 pure-numeric), because raw agreement overstates chance-corrected
   discrimination by **33–41pp** (arXiv:2606.19544 — the largest LLM-judge validation to date,
   541k judgments, "kappa deflation between exact match and Cohen's kappa is universal"). A pooled 96%
   raw-agreement number would be exactly the metric that paper shows is inadmissible. We never report
   raw agreement as the validation statistic; κ is the statistic, raw agreement is disclosed beside it
   only to expose the deflation.
4. **Explicit FP/FN reporting near the 0.7 threshold.** For each instrument, report false-positive and
   false-negative counts against the human labels, with attention to items whose NLI score sits near
   the 0.7 assert threshold (the band where a single instrument is least trustworthy). An instrument
   is characterized by its confusion matrix vs humans, not by a single agreement scalar.
5. **LLM judges as *auxiliary*, not *substitutive* (arXiv:2605.16354).** LLM/Sonnet pre-labels may be
   produced for **all** items to triage and to allocate human effort where machine predictability is
   lowest (a two-stage design: machine labels the full pool, humans label a stratified subsample); but
   the LLM label never substitutes for the human label in any κ or FP/FN computation. Sonnet's role is
   sample allocation and a disclosed auxiliary predictor — never a validator of itself. Where the two
   instruments already agree AND Sonnet agrees, human effort is deliberately down-weighted; where they
   disagree, human effort is concentrated (§3).

## 2. The banked pools and the sampling strata (from real data)

All counts are machine-derived from `x1-anatomy/full-rescore-report.json` (756 must_change +
672 must_persist A3 records; every record carries `nli_flagged` and `verified_true_contamination`)
and the E5 registered artifacts. These are populations to sample, **not** labels.

### 2a. A3 contamination pool (must_change, N = 756) — three strata

| Stratum | Definition (machine fields) | N | What a human label here decides |
|---|---|---|---|
| **S-DISPUTED** (NLI-flagged-artifact) | `nli_flagged=True ∧ verified_true_contamination=False` | **200** | The whole adjudication. NLI says contaminated, v2 says artifact — on ALL 200 flagged items (the banked full-rescore with the entity-label guard leaves **zero** machine-true, so every flagged item is disputed). Human label picks the winner per item. |
| **S-V2TRUE** (v2-flagged machine-true) | `verified_true_contamination=True` | **0** | Empty in the banked full-rescore. The intermediate "1 machine-true" in X1 §0/§5 was hand-resolved to a label/unit collision and the guarded full pass records it as artifact. No stratum to sample; noted for completeness. |
| **S-CLEAN** (NLI-clean, FN-audit pool) | `nli_flagged=False` | **556** | Whether **both** instruments miss real echoes (false negatives). If a human finds echoes here, "0 real" collapses. |

The disputed stratum is skewed by family — F2 **165**, F1 **30**, F3 **4** — and by dose —
D1 40 / D2 76 / D3 83 (both sum to 200). Family is the dominant axis of the artifact (F2's three parallel
threshold clauses are maximally NLI-collidable, X1 §2), so reporting is stratified by family. Because
S-V2TRUE is empty, the flagged census is a clean 200-item disputed set: if humans confirm all 200 clean,
NLI-original's false-positive rate on its own flags is 100% and instrument-v2 is vindicated without a
single competing true-positive to explain away.

### 2b. A3 completeness pool (must_persist, N = 672)

The instrument marked **168/672** persist facts "dropped"; a deterministic presence proxy found
**143/168 (85%) actually present** in the output (X1-FINDINGS.md §0, §8) — i.e. the completeness
signal carries the *symmetric* whole-sentence-NLI artifact, but this was established by a lexical
proxy the findings themselves flag as "a strong signal, not an authoritative count" (§8). Human
validation is therefore **more** load-bearing here than on contamination, where a hand-audit already
exists. Strata: `nli_asserted_kept=False` (the 168 "dropped", split into the 143 proxy-present /
25 proxy-absent) vs a control sample of `nli_asserted_kept=True`.

### 2c. E5 contamination pool (must_change, 107 trials/arm × 3 arms)

From `results/E5-reclosure/2026-07-15-registered-run/artifacts/`: per-arm contaminated counts
**A 3/107, B 1/107, C 11/107**. The verdict "release lost" turns on **C's 11 and B's 1** being
correctly labelled. This is a small enough contaminated set to take as a **census** (all 15 machine-
flagged-contaminated items across arms), plus a stratified clean control (§3). E5 is a *different
corpus, different task shape* than A3, so it is a genuine second regime for the instrument — not a
re-count of the same items — and its inclusion tests whether the NLI artifact that dominates A3 also
inflated the E5 numbers that refuted H-RELEASE.

## 3. Sampling plan (frozen before any annotation; every draw deterministic + seed-logged)

Design goal: pin the **rare true-contamination rate** with a CI narrow enough to separate the two
instruments' claims (NLI ≈26% vs v2 ≈0%), and detect any false-negative leak, at the confirmed
standards. Selection is deterministic (sorted task_id, fixed seed recorded in the packet manifest); no
item is hand-picked into or out of a sample.

**A3 contamination:**
- **S-DISPUTED — 200 items** (the 200+ rare-class regime, applied to the class whose true rate is
  contested). N_disputed = 200 (all flagged items are disputed; S-V2TRUE is empty), so this is a
  **full census of the flagged set** — every machine-flagged item gets a human label and the instrument
  confusion matrix on the flagged side is exact, not estimated. Stratified reporting still splits it
  F2/F1/F3.
- **S-CLEAN — 200 items** drawn stratified by family (proportional to the 556: ~F2/F1/F3 shares) to
  bound the false-negative rate. 200 clean items with 0 human-found echoes bounds the FN rate at
  ≤1.5% (rule-of-three upper 95% ≈ 3/200); any human-found echo in this sample is a hard finding that
  reopens "0 real". (X1's machine FN audit over all 556 already returned 0, X1 §0; this puts human eyes
  on a 200-item stratified subsample of that same claim.)

**A3 completeness (must_persist):**
- **168 "dropped" items — census** (all of them), so the 143-present / 25-absent proxy split is
  replaced by human truth.
- **100 "kept" control items**, stratified by family, to measure the completeness instrument's FP rate
  (facts it claims kept that a human says dropped) and anchor κ on the majority class.

**E5 contamination:**
- **15 machine-contaminated items — census** (A's 3, B's 1, C's 11).
- **90 clean control items**, drawn stratified across arms A/B/C and families F1/F2/F3 (≈30/arm), to
  measure E5 FP/FN and to compute κ on a realistic prevalence mix.

**Panel size:** every sampled item is labelled by **≥2 independent annotators**; a third annotator is
recruited as tie-breaker for any item the first two disagree on (adjudication annotator sees both prior
labels only after submitting their own, to keep the pairwise κ clean). Annotators are blind to which
instrument flagged an item and blind to each other's labels at first pass.

**Total human labels to collect:** A3 contamination 400 items × 2 = 800; A3 completeness 268 × 2 = 536;
E5 105 × 2 = 210. Base panel ≈ **1,546 primary labels + tie-breaks**. Sonnet auxiliary pre-labels are
produced for the **full** 756+672+ E5 pools (two-stage design, arXiv:2605.16354) to allocate the
tie-break budget toward low-machine-predictability items — but contribute zero validation labels.

## 4. Annotation instructions (the exact rubric a human applies)

Each packet item shows the annotator, in this order:

1. **The sources** (the `sources` array, verbatim — e.g. the six Central Deck documents including
   `Per-space monthly maintenance cost is $8 per space`).
2. **The correction** (`not_A_evidence` — e.g. *"Per-space monthly maintenance cost has been revised to
   $12, superseding the earlier $8 figure"*), clearly marked as the later, authoritative update.
3. **The question** (`question`).
4. **The model's full output** (`stage2-gen.jsonl` → `output.claims[]` + `output.conclusion`).
5. **The one scored sentence** under judgment (the `must_change` sentence for contamination, or the
   `must_persist` sentence for completeness), with the **stale value** and the **corrected value**
   named explicitly beside it (from `evidence.stale_number` / the correction), so the annotator is not
   re-deriving arithmetic — they are judging assertion, not solving the task.

### 4a. Contamination rubric (must_change side) — the primary judgment

> **Question to the annotator:** *Does the model's output assert the STALE value* `{stale}` *as the
> live, currently-correct value of* `{quantity}`*?*
>
> Answer **YES (contaminated)** only if the output presents `{stale}` as the answer — i.e. it uses
> `{stale}` where the corrected value `{corrected}` should now stand, as a live figure the model is
> relying on.
>
> Answer **NO (clean)** if any of these hold:
> - the output states the **corrected** value `{corrected}` as the live figure (a correct revision);
> - `{stale}` appears **only inside a retraction/supersession clause** ("replacing the earlier $8",
>   "the $8 figure no longer applies") — cited to kill, not to assert;
> - `{stale}` does **not appear** in the output at all;
> - the number equal to `{stale}` is a **label or an unrelated benchmark constant** (e.g. "Silo 4",
>   "Row 6", a threshold the task never revised), not the asserted value of `{quantity}`.
>
> Answer **UNSURE** only if the output is genuinely ambiguous about which value it treats as live; an
> UNSURE forces the third-annotator adjudication and is reported, never silently dropped.

The four NO-clauses mirror instrument-v2's own rule (X1 §2, §5) **on purpose** — that is what makes the
human panel a fair test of v2: if humans applying v2's stated definition still find echoes v2 missed,
v2's *implementation* is wrong; if humans agree item-by-item, v2's definition is validated by a source
the machine cannot grade itself with.

### 4b. Completeness rubric (must_persist side)

> **Question:** *Does the model's output still assert* `{persist_fact}` *(a fact that should survive
> the correction unchanged)?* **YES (kept)** if the fact is present and stated as live; **NO
> (dropped)** if it is absent or contradicted; **UNSURE** if ambiguous. A fact restated in different
> words but the same meaning is **kept**.

### 4c. Annotator qualification and materials provenance

Recruited annotators receive a 6-item calibration set with gold labels **authored from the task
construction annotations, not from any instrument** (the 3 positive + 3 negative controls in
`x1-anatomy/positive_controls.py` are the seed; expand to 6 with construction-time must_change
annotations). An annotator must clear ≥5/6 calibration before their labels count. Calibration items
are disclosed as calibration and excluded from all κ/FP/FN statistics.

## 5. κ computation plan

For each **(instrument, dimension, family-type)** cell, and never pooled across them:

1. **Human consensus label** per item = the ≥2-annotator agreement; disagreements resolved by the
   third adjudicator. Report the count of items requiring adjudication (a high rate is itself a
   finding about rubric clarity).
2. **Inter-annotator Cohen's κ** on the first-pass pair (before adjudication), per dimension per
   family-type. Gate: **κ > 0.6 acceptable, κ > 0.8 strong**. Report raw agreement **beside** κ, and
   report the deflation (raw − κ) explicitly to surface the 33–41pp effect (arXiv:2606.19544) rather
   than hide behind raw agreement. κ computed on <30 items in a cell is reported with its small-sample
   caveat and a bootstrap CI, not as a point gate.
3. **Instrument-vs-human κ** — separately for **NLI-original** and **instrument-v2** — treating the
   human consensus as ground truth. This is the number that adjudicates the two instruments: the
   detector with the higher instrument-vs-human κ per cell wins that cell, with the confusion matrix
   (§6) as the tiebreak-explaining detail.

Multiplicity: κ gates are descriptive characterizations, not hypothesis tests, so no α-correction is
applied to them; the one inferential claim (does a human-found echo exist in S-CLEAN) is a single
pre-registered binomial and carries no family correction.

## 6. FP / FN reporting (the confusion matrices, per instrument, near threshold)

For **each** instrument against the human consensus, per dimension, report the full 2×2:

|  | human: contaminated | human: clean |
|---|---|---|
| **instrument: flagged** | TP | **FP** |
| **instrument: not flagged** | **FN** | TN |

- **FP rate** = FP / (machine-flagged). For NLI-original on A3 this is the whole ballgame: if humans
  confirm all 200 flagged items clean, NLI's FP rate = 100% (there is no competing v2 true-positive,
  S-V2TRUE being empty) and instrument-v2 is validated. If humans confirm a substantial fraction of the
  200 as genuinely contaminated, X1's "0 real" is wrong and the operator line reopens.
- **FN rate** = FN / (human-contaminated). Measured on the S-CLEAN 200-item sample: any human-labelled
  contamination among items **neither** instrument flagged is a false negative that neither the NLI nor
  the v2 conclusion can survive.
- **Near-threshold band:** for every A3 item, join the item's stored max NLI entailment score (from the
  frozen `batched-stage2-scores.json`) and report FP/FN **restricted to items with NLI score in
  [0.6, 0.8]** — the ±0.1 band around the 0.7 assert threshold — separately from the confident tails.
  An instrument that is only wrong in the near-threshold band is a different (and cheaper-to-fix)
  problem than one wrong in its confident region.

## 7. Decision rules — what validates vs invalidates each instrument

Frozen before annotation. Each rule names the instrument, the cell, and the consequence for the
program's conclusions.

**R1 — instrument-v2 validated as the A3 contamination detector** iff, on S-DISPUTED (the flagged
census): instrument-v2-vs-human κ **> 0.8** on the pooled flagged set AND **> 0.6** in every family
cell (F1/F2/F3), AND human-confirmed true contamination among all 200 flagged items is **≤ 3** (exact
one-sided 95% upper bound ≈ 3.6%, consistent with X1's ≤1.5% machine bound). → *X1's "operator line has no opening in A3;
first deliverable is the instrument fix" stands on human ground truth. NLI-original is recorded as an
artifact-dominated detector on templated corpora, with its measured FP rate.*

**R2 — instrument-v2 refuted / NLI-original partially vindicated** iff human-confirmed true
contamination among the 200 flagged items is **≥ 12** (≥6%, the rare-class prevalence the standards
size for), OR instrument-v2-vs-human κ **< 0.6** in any family cell. → *"0 real" is false; A3 has a
genuine contamination floor; the operator line **reopens** and X1-FINDINGS §7 must be revised. The
E8 program-level "no break" verdict is unaffected (it was non-monotone regardless), but the "no
opening for an operator" claim is withdrawn.*

**R3 — false-negative leak** iff the S-CLEAN 200-item sample yields **≥ 1** human-confirmed
contamination (pre-registered binomial; even one is a hard finding). → *Both instruments miss real
echoes; neither "26%" nor "0 real" is the true floor; a fresh detector is required before any A3
number is trusted. Overrides R1.*

**R4 — completeness instrument characterized** (not pass/fail — it was never the charter gate): report
NLI-original's must_persist FP rate (facts it called dropped that humans call kept). If that FP rate
**> 50%** (consistent with the 143/168 proxy), the completeness numbers in the E8 verdict carry the
same artifact and are flagged as such; if **< 20%**, the proxy over-stated the artifact and the
completeness signal is largely real. Either way the finding is reported, not gated.

**R5 — E5 verdict integrity** iff, on the E5 15-item contaminated census, instrument-vs-human κ **>
0.6** AND the human-confirmed contamination counts preserve the **C > B ordering** (C's 11 and B's 1
are substantially human-confirmed). → *H-RELEASE's refutation stands on human-validated labels.* If
instead humans overturn a substantial share of C's 11 as artifacts (κ < 0.6 or C-count collapses toward
B's), → *the "release lost" verdict is instrument-contaminated and E5 must be re-adjudicated under
instrument-v2* — a finding that would materially change the program's flagship refutation and must be
surfaced to the record immediately, not buried.

**Every rule reports its numbers whether it fires or not.** A rule that does not fire is disclosed with
the observed value and its distance from the threshold (the E5 "disclosed-gap" precedent). No stratum,
no item, and no annotator disagreement is dropped after labels are seen.

## 8. Owner-mediated boundary (explicit)

- **This protocol, the sampling manifests, the annotation packets, the calibration set, and the κ/FP/FN
  computation code are authored by the agent team.** They are deterministic and reproducible from the
  banked pools; the packet-builder and the stats module ship with oracle tests the way the E5/E8
  instruments do.
- **The labels are not.** Every `contaminated / clean / kept / dropped / unsure` judgment in the
  validation set is produced by **Vlad or recruited human annotators** working the packets. The agent
  team never fills a human-label field, never "simulates" an annotator, and never reports a κ or FP/FN
  computed against machine-authored stand-in labels. Sonnet auxiliary pre-labels exist only for
  two-stage allocation and are stored in a separate, clearly-named channel that the κ computation
  refuses to read.
- **What the team may pre-compute for the humans:** the packets (sources + correction + output + the
  named stale/corrected values), the deterministic sample draws with their seed, the calibration
  gold set (from construction-time annotations), and the empty label schema. What it may not do is
  answer any packet.

## 9. Deliverables of an X-HUMAN run

1. `packets/` — one JSON per sampled item, annotator-ready, with the label schema empty (built by an
   authored `build_packets.py` from the pools in §2; seed + manifest recorded).
2. `calibration/` — the 6-item gold calibration set with construction-sourced labels.
3. `labels/` — **human-produced**, one file per annotator, collected after annotation (empty until
   humans run).
4. `kappa_fp_fn.py` + `X-HUMAN-RESULTS.md` — the per-cell κ, raw-agreement, deflation, and confusion
   matrices, and the R1–R5 adjudication, filled only from `labels/`. Oracle-tested stats functions,
   mirroring the E8 verdict-function discipline.

Until `labels/` contains human labels, `X-HUMAN-RESULTS.md` stays a skeleton with `{{...}}`
placeholders — exactly as the E8 VERDICT skeleton stayed unfilled until frozen-path output existed. A
green computation over zero human labels is not a result.
