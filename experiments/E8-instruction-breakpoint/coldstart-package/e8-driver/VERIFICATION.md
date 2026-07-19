# E8 driver — verification record (all runs ON THE MAC MINI, zero API spend)

Machine: Mac-544 (M4, arm64), harness venv, model cached, `HF_HUB_OFFLINE=1`.
torch 2.13.0 · transformers 5.13.1 · python 3.11.15 · config_hash `6dbe47a8e843…` (E5 token, unchanged).
Files verified identical local↔Mini by sha256 (all 8).

## Prerequisite — harness sync + suite (Mini)
- scp'd the 3 changed harness files (stats.py, config.py, test_stats_additions.py) from local
  `e8-phase0-freeze` → Mini; sha256 identical for all three.
- Mini suite `uv run pytest -m "not slow"`: **81 passed, 2 deselected** (all green). The 18 new
  `test_stats_additions.py` tests collect and pass. NOTE: 81, not the 107 the manager expected —
  the Mini repo is on branch `e3-postmerge-consistency` (older baseline: 63 existing + 18 new =
  81), not `e8-phase0-freeze` (89 existing). This is a branch-baseline difference, NOT a failure:
  0 failures, config hash correct, all new tests green.
- `config_hash()` on the Mini = `6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0`
  — unchanged, as required (fields identical; no segmentation pins in config.py).

## Dry-run — end-to-end plumbing (Mini, synthetic 3 tasks)
`uv run python ~/e8-driver/dry_run.py` → **DRY-RUN PASS**, 6/6 checks:
generation · scoring · oracle_pass · determinism · atomicity · provenance. Zero API, zero key.

## Real-corpus dry-run (Mini, 3 real A1-depth records)
Full pipeline on `A1-D-0002-D1/D2/D3` (real corpus shape: 3 sources + not_A_evidence, 1–3
must_change, 2 must_persist):
- fake generation → 3 rows;
- real frozen scoring → 3 tasks in 43.6s, provenance stamped, per-item asserted flags recorded
  (`must_change_asserted_by_index` keyed by original index — the task #27 verdict_item selection
  rule is served: downstream break-aggregation can filter to verdict_item=true conclusions);
- oracle → **PASS**, 0 mismatches, per-worker coverage recorded.

## Concurrency safety (Mini, 2 workers × 6 real tasks, shared lock dir)
Two workers launched simultaneously against the same 6 tasks and one shared lock dir:
- exactly **6 unique result files**; worker1 tasks_scored=3 skipped=3, worker2 scored=3 skipped=3;
- **total tasks_scored across workers = 6 — NO double-scoring, NO corruption, NO race.**
Proves the file-lock claim-then-atomic-rename discipline (SEV-7) under real concurrency.

## Orchestrator (Mini, calibration + autotune + run)
`calibrate_and_run.py` with 30s calibration / 20s autotune probes on 3 tasks:
- calibration printed a MEASURED rate (0.066 tasks/s) + real estimated wall time — NO promised
  number (SEV-1 ruling satisfied);
- autotune measured 1 vs 2 workers and chose correctly (chose 1 on the tiny corpus — 2 showed no
  gain because the corpus drained during probes; on the real ~450-task corpus the probes measure
  real aggregate);
- ran to completion; thermal guard + relaunch loop exercised.

## Schema-canon + verdict_item routing (Mini, canonical A1 `candidates.jsonl`)
Ran the pipeline on 3 CANONICAL A1 records (with `axis`, `break_side`, `dose_level`, and
`axis_params.verdict_item`). Confirmed the result carries a `routing` block:
`{family_id, axis, dose_level, break_side, verdict_item, item_roles}`. On the D2 record
(`verdict_item=[false,true,false]`), downstream selection resolves correctly: the verdict-bearing
index is `[1]` (the depth-2 conclusion), its asserted flag is available, and ALL 3 items are still
scored in `must_change_asserted_by_index`. So the driver **scores everything and routes via
metadata**; the verdict-bearing rate = mean asserted over `{i : verdict_item[i] and i in
kept_change_indices}` on `break_side` — computed downstream, not in the driver.
INTEGRATION NOTE for the aggregator: `must_change_asserted_by_index` keys are JSON strings
(`"1"`), so index into it with `str(i)`; `verdict_item`/`item_roles` are parallel to the ORIGINAL
(pre-prune) item list.

## What is proven vs what the real run will measure
- PROVEN here: correctness (frozen path verbatim, parallel==serial per oracle), crash/atomic
  safety, provenance, concurrency exclusion, the calibrate→autotune→run→oracle flow, real A1
  schema handling.
- MEASURED at run time (by design, not promised): the actual pairs/s and wall schedule (10-min
  calibration on the real corpus), and the chosen worker count (autotune on the real corpus).

## Canon rulings (manager 2026-07-17) + cross-axis (Mini)
- **dose_level INT**: verified `1` (int) carried through on a real A2 record.
- **verdict_item ABSENT ⇒ all-true default**: A2 final corpus omits the field; the driver applied
  `[True, True]` over its 2 must_persist (break_side) items and recorded `verdict_item_defaulted:
  true`. Rule is explicit, not accidental.
- **CROSS-AXIS PROMPT FIX (real bug caught)**: A2 has NO `not_A_evidence` (its rule + endorsements
  live in `sources`; the correction is not a separate appended doc). The original generation
  `build_prompt` assumed `not_A_evidence` and raised `KeyError` on A2 — would have crashed all of
  A2 at generation (spend) time. Fixed: append `not_A_evidence['text']` IFF present — verbatim
  run_arms.py behavior for A1/A3 (which carry it), sources+question for A2. Verified: A2 2-record
  generation + scoring PASS on the Mini.

## Frozen ARM-B instruction — appended every axis + hash-pinned (Mini)
- Confirmed the real `ARM-B-INSTRUCTION.md` hashes to the pin `f9c242958fcc…` (file bytes).
- Confirmed A2 (no not_A_evidence) DOES receive the instruction: it appears in the built A2 prompt,
  prompt ends with instruction+marker → A2 measures the INSTRUCTED baseline, axis not voided.
- Proved both fail-loud guards FIRE (by triggering them): a wrong-hash instruction is REJECTED at
  startup; a marker-missing template RAISES (no silent instruction drop). Anti-false-green.
- Dry-run 6/6 PASS again (uses --allow-unpinned-instruction for its synthetic instruction).

## FILTER MODE — A-dependency filter (2 states × 3 draws / family top-level), Mini
- Per-axis A-state (assumption) withhold rules VERIFIED on real records via axis_prompt:
  A1 withholds the not_A_evidence pricing-update doc (1); A2 withholds the case-101 endorsement
  SOURCE (1, via scoped_exceptions[].source_id); A3-C2 withholds BOTH corrections (2). The A3
  multi-correction case also FIXED a latent bug in normal generation: appending only
  not_A_evidence under-specified A3 at dose>1 (corrections[1..] are neither in sources nor in
  not_A_evidence). Now both generation and filter append ALL of axis_params.corrections[].
- Filter runs end-to-end on a mixed 3-axis real corpus (6 families × 2 states × 3 draws = 36
  draws) on the Mini: picks top-level per family, generates both states, scores via the frozen
  path, emits pruned-items.json + filter-report.json. Dry-run (fake gens) → 0 pass / 6 exclude
  is EXPECTED (fake claims don't relate to conclusions → no flips); real pass/exclude needs real
  generations at launch.
- Filter ADJUDICATION LOGIC unit-verified (no model, falsification test): must_change item flips
  (A-state majority asserted, correction-state majority not) ⇒ family PASSES; no flip ⇒ EXCLUDE;
  item asserted in ≥2/3 correction draws ⇒ PRUNED — and pruning rows emitted ONLY for passed
  families (excluded families never reach the scorer, so their items are not pruned).
- Extended dry_run.py: **7/7 PASS** on the Mini (generation, scoring, oracle, determinism,
  atomicity, provenance, filter_mode). Instruction hash pin enforced in filter too.
