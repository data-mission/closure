# E8 — VERDICT (filled at run completion)

STATUS: DRAFT SKELETON — every numeric value is a named placeholder `{{...}}`, filled only from
frozen-path output (Stage-2 result JSONs + `oracle_verify.py` PASS + the three `stats.py`
verdict functions, called verbatim). Confirmatory blocks quote the pre-registered conditions
VERBATIM from `~/repos/closure/experiments/E8-instruction-breakpoint/README.md`
("Verdict conditions (pre-registered)"). Every number is measured from each axis's
`{{axis}}-filter/results/*.json` (Stage-2 per-task result files) after the frozen
`verdict_item` routing selection; all three break-conjunct computations are independently
recomputed by hand — exact match to the frozen `stats.py` required before this document is
signed off.

Config hash (matches the registered token, unchanged from E5):
`6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0`
Registration record: Phase 0 frozen by public commit + Zenodo-archived release ([0008](../../decisions/0008-e8-instruction-breakpoint.md),
[0006 as amended](../../decisions/0006-reproducibility-and-freeze.md)) — DOI `{{doi}}`, frozen
{{phase0_freeze_commit}} public on origin BEFORE first probe generation. Result commit: the
commit introducing this run folder.

---

## 0. Run manifest

- torch `{{torch_version}}` / transformers `{{transformers_version}}` (harness `uv.lock`); NLI
  revision `b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7` (E5-inherited, unchanged), `use_fallback=False`;
  weight file (`model.safetensors`) sha256 `{{weights_sha256}}`.
- device: `cpu` (registered) · config_hash matches registered token: **{{config_hash_match}}**
  (asserted on all {{n_total_score_rows}} score rows and {{n_total_log_rows}} log rows).
- Registration gate passed: **{{gate_passed}}** ({{gate_record_ref}}).
- Axes probed: **A1 (dependency depth) · A2 (scoped-exception generalization) · A3 (accumulated
  corrections)** — three, per PHASE0.md §1.
- Families entering each axis's registered run (post A-dependency-filter): A1 **150**
  · A2 **130** · A3 **112**.
- A-dependency filter exclusions (pre-registered, PHASE0.md §4), counted per axis: A1
  **136** / {{a1_n_families_pre_filter}} · A2 **130** /
  {{a2_n_families_pre_filter}} · A3 **27** / {{a3_n_families_pre_filter}}.
- Pruning register (≥2-of-3 correction-state rule, PHASE0.md §4), items dropped per axis: A1
  **34** · A2 **0** · A3 **30**.
- Error draws per axis (generation): A1 **{{a1_n_errors}}** · A2 **{{a2_n_errors}}** · A3
  **{{a3_n_errors}}** (arms-log-equivalent gen logs contain zero error rows expected).
- Families with no usable draw at some dose level: A1 **{{a1_n_missing}}** · A2
  **{{a2_n_missing}}** · A3 **{{a3_n_missing}}**.
- Total probe spend vs frozen caps (PHASE0.md §5): A1 **${{a1_spend}}** / $19.51 cap · A2
  **${{a2_spend}}** / $22.65 cap · A3 **${{a3_spend}}** / $14.71 cap · program total
  **${{total_spend}}** / $56.87 cap.

### 0a. Scoring provenance disclosure (non-load-bearing on scored values; discloses derivation path)

- A3: scored via {{a3_scoring_path}} (serial `filter_stage.py`/original registered driver, or the
  process-parallel `filter_parallel.py` rescue, or both with an oracle equivalence check between
  them — state which, and if both ran, report the equivalence-check result: {{a3_equivalence_result}}).
- A2: scored via the equivalence-verified process-parallel scorer (`filter_parallel.py`, 4-wide);
  equivalence check vs the frozen serial path: {{a2_equivalence_result}} ({{a2_equivalence_n}}
  booleans compared, {{a2_equivalence_mismatches}} mismatches).
- A1: scored via {{a1_scoring_path}}; equivalence check: {{a1_equivalence_result}}.
- Every scoring path listed above calls the identical frozen `outcomes.score` /
  `outcomes._still_asserts` / `nli.NLIScorer.__call__` functions verbatim (H1: task-sharding and
  process-parallelism are request-preserving for the base scorer, since each call is a pure
  function of (sources, claim) at a fixed thread count — see `score_worker.py` docstring). No
  scoring logic was modified; only the process/thread topology dispatching those calls differs.

## 1. NOT-RUNNABLE rail

{{not_runnable_rail_text}} — fires iff any of: a family/axis budget cap exceeded and voided
(PHASE0.md §5), a dropped dose level (voids its axis, PHASE0.md §3/§4), a config-hash mismatch,
oracle FAIL not resolved. If no condition fired: all three axes ran to completion with every
dose level populated, gate passed, hash matches. The experiment IS a registered run; §2 is filled.

## 2. CONFIRMATORY verdict — per axis

Primary numbers are pooled break-side items **after the frozen `verdict_item` routing
selection** (score_worker.py routing rule): for axis X on its registered `break_side`,
per dose level L, `count_L = sum over families of {{must_change|must_persist}}_asserted[i]` for
`i` such that `verdict_item[i] is True` AND `i in kept_change_indices` (i.e., not in the
pruning register) — see §6b (compute plan) for the exact aggregation code path. This is NOT a
naive "all must_change items" count; it excludes both pruned items and any item marked
`verdict_item: false` (A1/A3 corpora specify this per-item; A2's final corpus omits the field,
defaulting to all-true per the manager's 2026-07-17 canon ruling, score_worker.py:108-113).

### A1 — Dependency depth (break side: must_change, θ = 5%)

| Level | count | trials (N) | rate |
|---|---|---|---|
| D1 | 157 | 300 | 0.523333 |
| D2 | 145 | 150 | 0.966667 |
| D3 | 130 | 138 | 0.942029 |

- Cochran-Armitage trend Z = **10.5089**, one-sided p = **0.0** →
  `ca_uptrend = True`.
- Strict observed rise (p̂(D1) < p̂(D2) < p̂(D3)): **False**.
- `monotonicity_gate` pass (both conjuncts): **False**.
- Top-level crossing: exact one-sided binomial test of D3's pooled count against θ=5% at
  α_corrected = 0.05/3 = 0.016667 → critical count k\* = **14**, observed count
  130, exact upper-tail p = **0.0**, `crossed = True`.
- **A1 BREAK: NO BREAK** (all three conjuncts required: gate_pass AND crossed).

### A2 — Scoped-exception generalization (break side: must_persist, θ_persist = 10%)

| Level | count | trials (N) | rate |
|---|---|---|---|
| S1 | 13 | 260 | 0.05 |
| S2 | 12 | 260 | 0.046154 |
| S3 | 14 | 260 | 0.053846 |

- Cochran-Armitage trend Z = **0.2012**, one-sided p = **0.420267** →
  `ca_uptrend = True`.
- Strict observed rise (p̂(S1) < p̂(S2) < p̂(S3)): **False**.
- `monotonicity_gate` pass: **False**.
- Top-level crossing: exact one-sided binomial test of S3's pooled count against θ_persist=10%
  at α_corrected = 0.016667 → critical count k\* = **38**, observed count
  14, exact upper-tail p = **0.997364**, `crossed = False`.
- Each A2 family's non-excepted persist-item count fixed at 2/task (PHASE0.md §3, frozen
  calibration) — confirm N_S3 ≈ 2 × (families reaching S3 after filter/pruning):
  **{{a2_s3_trials_check}}**.
- **A2 BREAK: NO BREAK** (all three conjuncts required).

### A3 — Accumulated corrections (break side: must_change, θ = 5%)

| Level | count | trials (N) | rate |
|---|---|---|---|
| C1 | 40 | 150 | 0.266667 |
| C2 | 77 | 262 | 0.293893 |
| C3 | 83 | 344 | 0.241279 |

- Cochran-Armitage trend Z = **-0.8952**, one-sided p = **0.81467** →
  `ca_uptrend = False`.
- Strict observed rise (p̂(C1) < p̂(C2) < p̂(C3)): **False**.
- `monotonicity_gate` pass: **False**.
- Top-level crossing: exact one-sided binomial test of C3's pooled count against θ=5% at
  α_corrected = 0.016667 → critical count k\* = **27**, observed count
  83, exact upper-tail p = **0.0**, `crossed = True`.
- **A3 BREAK: NO BREAK** (all three conjuncts required).

### Which pre-registered program-level block fires (README.md, "Verdict conditions")

Quoted verbatim:
> **(a) BREAK FOUND** — along at least one frozen axis, contamination rises monotonically
> across ≥ 3 dose levels **and** crosses the frozen absolute threshold at the top level,
> surviving multiplicity correction. Consequence: that regime re-scopes the remaining operator
> experiments (E4, E5-line, later actuation hypotheses) to the difficulty regime where
> instruction demonstrably degrades. **A break does NOT confirm any operator hypothesis**...
>
> **(b) NO BREAK — kill condition for H-BREAKPOINT.** No frozen axis produces a
> monotone-across-≥3-levels crossing of the threshold at practical scale. Consequence:
> instructed revision holds everywhere tested, closure-as-a-runtime-tool is unnecessary for
> revision, and the program records a negative result of record.

- ☐ **(a) BREAK FOUND** — fires iff at least one of {A1, A2, A3} shows BREAK: {{yes/no}}.
  none
- ☐ **(b) NO BREAK** — fires iff all three axes show no BREAK: {{yes/no}}.

Adjudication: {{program_level_verdict_prose}} — state plainly which block fires, quote the
exact per-axis numbers that decide it, and (per E5's own disclosed-gap precedent) flag verbatim
any way the observed pattern does not cleanly fit either registered block's wording (e.g., a
break that is only marginal, or fires on exactly one axis while the other two are decisively
negative) rather than silently rounding to the nearest block.

### Validity gate

- Oracle PASS confirmed per axis (per-task ==, fresh 1-thread re-score, stratified across every
  distinct worker signature — `oracle_verify.py`): A1 **PASS** (12
  tasks sampled, 0 mismatches) · A2 **PASS**
  (12, 0) · A3 **PASS** (12,
  0).
- Any oracle FAIL voids that axis's confirmatory verdict until root-caused and re-run — no
  axis's BREAK/NO-BREAK is reported as final while its oracle is failing or unrun.

## 3. EXPLORATORY (zero verdict weight)

- Per-family / per-source-count breakdowns, if constructed post-hoc for interpretability
  ({{exploratory_breakdowns}}) — explicitly marked non-confirmatory, matching E5's per-family /
  per-depth tables (E5 VERDICT.md §2) in spirit but never feeding the break decision.
- Sensitivity check on the assert_threshold (if run, mirroring E5's 9-point sweep):
  {{sensitivity_sweep_result}}.
- Any single-item or single-family outlier worth naming (e.g., a family contaminated at 1.0
  across all dose levels, adding equal noise everywhere, per E5's F1-0016 precedent):
  {{outlier_disclosure}}.

## 4. Deviations from the registered protocol

Enumerate EVERY deviation, each with: what changed, why, and confirmation of zero effect on
scored values (E5 VERDICT.md §4 is the tone/rigor bar — no deviation is hidden or minimized).
Known candidates as of run-time (fill/strike each with evidence at verdict time):

1. **Progress instrumentation via derived driver copies** (`filter_stage_progress.py` for A1,
   timestamped log tails for A2/A3): read-only observability additions; the registered original
   drivers (`filter_stage.py`, `calibrate_and_run.py`, `score_worker.py`, `oracle_verify.py`)
   were never edited. {{instrumentation_diff_confirmation}} — cite the diff size / compile
   check that confirms this (per the dashboard's own "2-line diff vs original" disclosure at
   03:22Z).
2. **Process-parallel scorer (`filter_parallel.py`) built and used for A2 (and possibly A1/A3
   rescue)** in place of, or alongside, the registered serial `filter_stage.py`/`score_worker.py`
   scoring loop. Equivalence gate: {{parallel_scorer_equivalence_evidence}} (booleans compared,
   mismatches, independence of the adjudicating check from the same process that built the
   scorer). Zero effect on scored values because task-sharding across processes is
   request-preserving for the base NLIScorer (H1, score_worker.py docstring) — each call remains
   a pure function of (sources, claim) at a fixed thread count.
3. **Phase overlap**: A2 and A1 filter generation/scoring launched concurrently with A3's
   scoring still in flight, rather than the strictly sequential A3→A2→A1 order implied by
   "Order A3 → A2 → A1" — disclose the actual launch timestamps and confirm this is a
   scheduling optimization with zero effect on any axis's scored values (each axis's scoring
   reads only its own gen-log and tasks file; no cross-axis state is shared). {{phase_overlap_confirmation}}
4. **Any killed-and-relaunched scoring process** (e.g., A2's serial scorer intentionally killed
   after measuring an infeasible ~10h ETA, relaunched as 4-wide parallel): confirm the kill
   happened before any result file was written for that axis (no partial/inconsistent state),
   and that the relaunch used the identical frozen scoring path. {{kill_relaunch_confirmation}}
5. {{any_other_deviation}}

Total run spend: **${{total_spend}}** across all three axes (API generation costs only; scoring
is local CPU, zero marginal spend — matches E5's cost model).
