# X4 — REUSE re-score pipeline (both tiers), wired for the Mini

Adopted path: re-score the BANKED A1 generations (filter + Stage-2) against the v2 corpus. No new
generation. The v2 corpus supplies the stale-polarity `must_change`; the banked gens supply the model
outputs (byte-identical prompts → same outputs). GPU/MPS scoring only.

## INDEX-MAPPING GUARD — verified safe (the load-bearing correctness check)

**There is NO index-carryover risk from the old corpus. Confirmed by tracing the frozen scorers:**

- Both scorers key must_change items from the CORPUS record's own list: `mc = task["must_change"]`
  — filter tier `batched_scorer.py:154`; Stage-2 tier `batched_stage2_scorer.py:103` (in
  `build_annotations`). With `--tasks A1-depth-v2.jsonl`, item_idx indexes the v2 must_change list
  (insurance already dropped), NOT the old corpus.
- The banked gens carry NO item structure. Gen indexing is `(task_id, arm)` → `{claims, conclusion}`
  for Stage-2 (`batched_stage2_scorer.py:80-88`) and `(task_id, filter_state, draw_index)` → output
  for the filter tier (`batched_scorer.py:114-119`). The model output is the NLI PREMISE; the
  must_change item is the NLI HYPOTHESIS sourced entirely from the v2 corpus. The gen cannot misalign
  item indices because it has none.
- Family selection: `top_level_per_family` (imported from filter_stage) runs on the v2 tasks → 149
  families (A1-D-0008 dropped). The 6 banked A1-D-0008 filter-gen rows are simply never requested — a
  strict subset, no misalignment.
- Gen selection hash: banked A1 gens carry config_hash `6dbe47a8…`, auto-detected from the gen log's
  first row (`batched_stage2_scorer.py:43`). The v2 re-score selects those exact banked gens.

**Net: the insurance drop and the A1-D-0008 family drop are transparent to scoring. Pruning is now
computed under correct (stale) polarity because adjudicate reads v2's must_change.**

## Pre-req (once): GPU device gate

`gpu_probe` (Step Zero) must have PASSED for the A1 corpus/model/DeBERTa on this Mini already (it did,
for the registered A1 run — same model, same checkpoint). No new probe needed; the corpus swap does not
change the scorer model.

---

## TIER 1 — FILTER re-score (banked filter gens × v2 must_change) → v2 pruned-items

Step 1a. GPU batched filter score (equiv gate + scored pass), reusing the banked A1 filter-gen:
```bash
ssh mac
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
GEN_LOG=~/e8-run/A1-filter/filter-gen.jsonl \
E8_RUN=~/e8-run \
DEVICE=mps THREADS=2 \
bash ~/e8-driver/run_axis_gpu.sh
```
- `run_axis_gpu.sh` runs `batched_equiv.py` (boolean-flip gate) then `batched_scorer.py`, writing
  `~/e8-run/A1V2-filter/batched-scores.json`. No generation.
- NOTE the GEN_LOG points at the ORIGINAL `A1-filter/filter-gen.jsonl` (reused). Out-dir is
  `A1V2-filter` (AXIS=A1V2) so nothing overwrites the registered A1 artifacts.

Step 1b. Reconstruct v2 pruned-items + filter-report from the batched scores (frozen adjudicate):
```bash
cd ~/e8-driver
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u filter_report_from_batched.py \
  --tasks ~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
  --batched-scores ~/e8-run/A1V2-filter/batched-scores.json \
  --out-dir ~/e8-run/A1V2-filter
```
Writes `~/e8-run/A1V2-filter/{pruned-items.json, filter-report.json}` — pruning under correct polarity.

---

## TIER 2 — STAGE-2 re-score (banked stage2 gens × v2 corpus + v2 pruning)

Step 2. GPU batched Stage-2 score (shard-equiv gate + scored pass + Option-C oracle), reusing the
banked A1 Stage-2 gen and the v2 pruned set:
```bash
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
GEN_LOG=~/e8-run/A1-stage2/stage2-gen.jsonl \
PRUNED=~/e8-run/A1V2-filter/pruned-items.json \
E8_RUN=~/e8-run \
DEVICE=mps THREADS=2 \
bash ~/e8-driver/run_stage2_gpu.sh
```
- GEN_LOG points at the ORIGINAL `A1-stage2/stage2-gen.jsonl` (reused); PRUNED at the v2 pruning.
- Writes `~/e8-run/A1V2-stage2/{batched-stage2-equiv.json, batched-stage2-scores.json, results/*.json,
  _oracle_result.json}`. No generation. Same equiv + oracle gates as the registered run.

---

## TIER 3 — VERDICT

Step 3. Compute the A1-v2 per-dose depth verdict from the v2 results:
```bash
cd ~/e8-driver
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u verdict_compute.py \
  --a1-results       ~/e8-run/A1V2-stage2/results \
  --a1-filter-report ~/e8-run/A1V2-filter/filter-report.json \
  --a1-pruned        ~/e8-run/A1V2-filter/pruned-items.json \
  --a1-expect-n 447 \
  --a2-results ~/e8-run/A2-stage2/results --a2-filter-report ~/e8-run/A2-filter/filter-report.json --a2-pruned ~/e8-run/A2-filter/pruned-items.json \
  --a3-results ~/e8-run/A3-stage2/results --a3-filter-report ~/e8-run/A3-filter/filter-report.json --a3-pruned ~/e8-run/A3-filter/pruned-items.json \
  --out ~/e8-run/verdict-prep/verdict-numbers-A1V2.json
```
- `--a1-expect-n 447` matches the v2 row count (partial-axis guard; a live/short results dir is flagged
  DRAFT-not-final until 447 result files exist).
- **verdict_compute carries a hardcoded A1 `validity_note` calling A1 "invalid AS BUILT (polarity
  inverted)".** That note is for the OLD corpus. For the v2 run the note is STALE and must be updated
  (or the A1V2 axis given its own note) before the number is presented — otherwise the report will
  contradict itself (v2 IS the polarity fix). This is a presentation edit, not a scoring issue; flag to
  whoever finalizes the verdict doc. The v2 per-dose numbers themselves are correct.

---

## What the verdict answers

Per-dose (D1/D2/D3) contamination on the CORRECTLY-polarized A1 depth axis: does the model still assert
the STALE derived value, and does that rate rise with chain depth (dose)? A monotone rise crossing
θ=0.05 = a real depth-breakpoint; flat/near-0 = instructed revision robust across depth. Either way the
depth question is settled on a valid axis (the pre-stated two-sided X4 conclusion).

## Stop / resume
Both `run_axis_gpu.sh` and `run_stage2_gpu.sh` are resumable and stoppable (`--stop A1V2`); they recompute
from banked gens, so a stop mid-score loses nothing. GPU-SOLO: do not co-run with another axis's scorer.
