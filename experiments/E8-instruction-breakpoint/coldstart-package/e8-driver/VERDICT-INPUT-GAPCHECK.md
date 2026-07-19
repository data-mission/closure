# Verdict compute-plan input gap-check (vs the GPU batched pipeline this mission produces)

Question (team-lead): are the compute plan's inputs all satisfied by the artifacts this pipeline
will produce — names, shapes, paths — so verdict computation has no surprise gaps when Stage-2
scoring lands? Answer: EVERYTHING is satisfied EXCEPT ONE — the oracle validity gate (§5). Detail below.

## Inputs the plan declares (verdict_compute-plan.md §1) vs what the pipeline produces

| Plan input | Produced by | Status |
|---|---|---|
| `{X}-filter/results/*.json` per-task Stage-2 results, score_worker.score_one_task shape | `batched_stage2_scorer.py --results-dir` → one `<task_id>.json` per task | ✅ SHAPE MATCH (17/17 fields, below) |
| `{X}-filter/results/_oracle_result.json` (§5 validity gate) | oracle_verify.py — CPU registered path ONLY; the GPU pipeline does NOT run it | ❌ GAP — see below |
| `corpus-candidates/{X}.jsonl` (item counts + verdict_item cross-check) | frozen corpus, committed | ✅ present, unchanged |
| `config.py → CONFIG.stats` (alpha, bonferroni) | frozen harness | ✅ present |
| `{X}-filter/pruned-items.json` (feeds Stage-2 --pruned; also §0 "n_pruned" disclosure) | `filter_report_from_batched.py` (built, byte-verified vs frozen smoke) | ✅ produced + gated |
| `{X}-filter/filter-report.json` (§0 n_families / n_excluded / n_pruned disclosure) | `filter_report_from_batched.py` | ✅ produced |
| stats.py verdict fns (monotonicity_gate, exact_binomial_crossing, bonferroni_alpha) | frozen harness | ✅ all 6 exist (grep-confirmed) |
| Deviations register (§6): dashboard events, run.log timestamps, git diff of drivers | ops artifacts / git | ✅ external to scoring; unaffected |

### Result-shape field match (plan §1 expected vs batched_stage2_scorer.build_task_results)
All 17 fields present and correctly typed: task_id, kept_change_indices, routing{family_id, axis,
dose_level, break_side, verdict_item, verdict_item_defaulted, item_roles}, arms{B{n_items,
contaminated_items, contamination, completeness, must_change_asserted_by_index (str-keyed by ORIGINAL
index), must_persist_asserted (positional list)}}. Plus provenance + ts.
- must_change_asserted_by_index is keyed by ORIGINAL index (score_worker.py:80-83 uses keep[j]) —
  matches the plan's aggregation `arms["B"]["must_change_asserted_by_index"][str(i)]` (§2 line 60).
  My scorer str-keys it (JSON requirement) — plan reads `[str(i)]`, consistent.
- dose_level is int (1/2/3) in all three corpora (verified) → matches plan's `routing.dose_level == L`.
- per-task filename = `<task_id>.json`, no `_` prefix → the oracle/aggregation `*.json` glob with
  `_`-prefix exclusion (§1 trap) includes them correctly.
- must_persist NOT pruned (plan §7 confirmed): my scorer scores full must_persist, kept applies only
  to must_change — matches score_worker.build_annotations exactly.

## THE ONE GAP: oracle validity gate (§5) has no producer in the GPU pipeline

`verdict_compute-plan.md` §5 REQUIRES `~/e8-run/{X}-filter/results/_oracle_result.json`
(PASS/FAIL) and blocks an axis's break_verdict if the oracle FAILED. In the registered pipeline
`launch.sh` runs `oracle_verify.py` as step 3, which re-scores a stratified sample in a FRESH
1-thread CPU process and demands per-task bit-for-bit equality, writing `_oracle_result.json`
(oracle_verify.py tail). The GPU Stage-2 pipeline (`run_stage2_gpu.sh` → batched_stage2_scorer) does
NOT run oracle_verify and produces NO `_oracle_result.json`. So as things stand, §5 has no input for
any GPU-scored axis, and VERDICT-skeleton §2 "Validity gate" cannot be filled.

### Why it's not a simple "just run oracle_verify too"
oracle_verify's SEV-4 purpose is to catch **per-worker environment corruption across a CPU worker
FLEET** (it stratifies by worker signature = hostname|threads|versions|config_hash, guaranteeing
≥min_per_worker sampled tasks per distinct worker). The GPU batched path is a SINGLE MPS process —
there is no worker fleet, so the specific failure mode oracle_verify guards (one corrupt worker
self-confirming on 1/3 of tasks) does not exist the same way. The GPU path instead introduces a
DIFFERENT validity question — batched-vs-per-call composition equivalence — which `batched_stage2_equiv`
already gates (zero boolean flips, per-item, vs score_worker.score_one_task on the same device).

### Three ways to close it (team-lead decides; I recommend C)
A. Run `oracle_verify.py` against the GPU per-task result files as-is. WORKS mechanically (my results
   carry `provenance`, filenames are `<task_id>.json`), and it re-scores on CPU 1-thread — but that
   re-introduces the slow CPU scorer for the sample, and it would be checking GPU results against a
   CPU re-score, i.e. a device cross-check, not the worker-corruption check it was designed for. Its
   PASS would actually be a strong CPU-vs-GPU per-task equivalence statement on the sample — arguably
   MORE than the registered oracle proved. Slow but defensible; produces a real `_oracle_result.json`.
B. Treat `batched_stage2_equiv`'s PASS as the validity gate and emit an `_oracle_result.json`-shaped
   record from it (verdict:"PASS"|"FAIL", n compared, n mismatches, elapsed) so §5 has its input in
   the expected shape. Fast, but changes what the gate MEANS (composition-equivalence, not fresh
   re-score) — must be disclosed in VERDICT §0a/§5 as a GPU-era substitution.
C. BOTH, layered (recommended): batched_stage2_equiv is the mandatory composition gate (already
   built); PLUS run oracle_verify on a small stratified sample of the GPU results as an INDEPENDENT
   fresh-process CPU cross-check that also yields the real `_oracle_result.json` §5 expects. This
   keeps the registered validity artifact AND adds the GPU-specific gate — the most defensible for an
   amended/registered run, and the CPU sample is small (stratified, not the full tier). A thin
   adapter (author on request) would: run batched_stage2_scorer to produce results/, then invoke the
   existing oracle_verify.py against that results/ dir (it already writes _oracle_result.json), with
   NO new scoring code — oracle_verify re-scores via the frozen score_one_task itself.

WHAT I DID NOT DO: I did not author the oracle adapter — whether to close the gap via A/B/C is a
validity-semantics decision for the lead, and C reuses the existing oracle_verify.py unchanged (just
needs wiring into run_stage2_gpu.sh as a step 3, gated on the equiv PASS). Say the word and I'll wire it.

## ADDENDUM (2026-07-18) — Option C ADJUDICATED + WIRED

Team-lead adjudicated the §5 oracle gap: OPTION C — layered gates. `batched_stage2_equiv` remains the
mandatory composition gate (covers batching/padding equivalence, zero boolean flips). ON TOP of it, a
bounded stratified fresh-CPU per-task re-score yields the real `_oracle_result.json` §5 reads — its
real meaning (fresh-process CPU instrument-identity per sampled task), NOT a repurposed boolean.
Rationale recorded: composition gate covers batching; oracle sample covers instrument-identity per
task on fresh CPU. Together: PASS+PASS ⇒ GPU Stage-2 scores trustworthy for §5.

WIRED — new file `stage2_oracle_sample.py` + `run_stage2_gpu.sh` step 3:
- oracle_verify.py stays BYTE-UNCHANGED. Mechanism (verified): it samples internally by worker
  signature over its `--out-dir` *.json glob and has no task-list flag, so we stage ONLY the chosen
  ~SAMPLE_CAP result files into a temp dir and run it with `--frac 1.0 --min-per-worker N`; single
  worker-sig bucket + frac 1.0 ⇒ it re-scores EXACTLY the staged sample on fresh CPU 1-thread.
- SAMPLE (bounded, ~12/axis): force-include any task with contamination>0 or verdict_item_defaulted;
  then cover every (dose_level × break_side) cell present; then round-robin fill to cap. Deterministic
  (sorted). Keeps CPU leg ~3-6 min/axis.
- DISCLOSURE: the emitted `_oracle_result.json` carries sample_composition (task_ids, per-stratum
  counts, n/total, forced count), sample_cap, verified_at, and a gpu_path_note stating exactly what
  PASSed (bounded stratified fresh-CPU cross-check, not full re-score, not the CPU-fleet corruption
  check).
- SEQUENCE: run_stage2_gpu.sh = equiv gate → scored pass → oracle sample gate. Oracle mismatch =
  loud FAIL, nonzero exit, axis verdict BLOCKED, report to lead — never auto-continue. The FAIL
  `_oracle_result.json` is still written (auditable).
- VERIFIED (stub-oracle end-to-end): stratification picks 12/20 incl. all forced; temp-dir staging
  makes oracle re-score exactly those 12; PASS writes disclosed `_oracle_result.json` to the real
  dir + exit 0; FAIL writes the disclosed FAIL record + exit 2; temp dir cleaned; real modules
  cross-import cleanly; run_stage2_gpu.sh parses under bash 3.2.

## Minor notes (not gaps)
- The plan's §2 trials cross-check ("≈1.78 items/task must_change, 2/task A2 must_persist") is a
  sanity assertion the aggregation code makes — my results carry n_items + the full asserted maps, so
  the check is computable. No missing input.
- The plan's §3 hand-recomputation of exact_binomial_crossing is an aggregation-side check; no
  scoring input needed from my pipeline.
- Spend caps (§0) come from PHASE0 + gen logs, not scoring — unaffected.
