#!/usr/bin/env bash
# =============================================================================
# run_stage2_gpu.sh — E8 STAGE-2 (registered-run) GPU (MPS) SCORING for ONE axis, gated + solo.
# =============================================================================
# Scores the banked Stage-2 Arm-B generations for one axis on MPS in three steps:
#   1. batched_stage2_equiv.py  — batched-vs-per-call composition gate (score_worker.score_one_task),
#                                 SAME device. EXIT-CHECKED: nonzero (a boolean flip) ABORTS before the
#                                 scored pass. MODE: full-axis by default; set EQUIV_N_TASKS=N for a
#                                 SHARD gate on the first N tasks — a throughput decision (full-axis
#                                 double-scores everything, ~20 min/axis). Shard mode is layered on the
#                                 already twice-proven (0-flips, this model/corpus class) composition
#                                 equivalence AND the per-axis stratified CPU oracle (step 3), which
#                                 still independently cross-checks the final numbers. The mode that ran
#                                 (full vs shard N) is recorded in the log + INTERVENTIONS.
#   2. batched_stage2_scorer.py — the scored pass, only if the gate PASSED. Writes one
#                                 score_worker-shaped JSON per task into <results-dir> (the verdict
#                                 compute-plan's input layout) plus an aggregate JSON.
#   3. stage2_oracle_sample.py  — bounded stratified fresh-CPU per-task oracle (Option C), yields the
#                                 real _oracle_result.json the verdict plan §5 reads.
#
# GPU-SOLO (16GB rule, GPU-REWIRE-NOTES §1): ONE model process at a time. Do NOT run this concurrently
# with the filter-tier run_axis_gpu.sh, the E5 re-anchor, or another axis's Stage-2. Sequence them.
#
# No API spend, no freeze gate (scoring only). Stage-2 gens carry the frozen CPU hash 6dbe47a8
# (generation never touches the scorer device — lead-confirmed); the scorer auto-detects that banked
# hash for record selection and moves ONLY the scorer to --device (reanchor_e5_mps pattern).
#
# CERTIFICATION CHAIN: gpu_probe device gate (Step Zero) must be green; this script's equiv gate is
# the Stage-2 composition gate on top of it.
#
# USAGE (Mini):
#   AXIS=A3 \
#   TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
#   GEN_LOG=~/e8-run/A3-stage2/stage2-gen.jsonl \
#   PRUNED=~/e8-run/A3-filter/pruned-items.json \
#   bash run_stage2_gpu.sh
#   Stop: bash run_stage2_gpu.sh --stop A3
# =============================================================================
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"     # uv resolves under nohup/caffeinate (launch.sh lesson)

DRIVER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="${CLOSURE_HARNESS:-$HOME/repos/closure/harness}"
E8_RUN="${E8_RUN:-$HOME/e8-run}"
INTERV="$E8_RUN/INTERVENTIONS.log"

if [[ "${1:-}" == "--stop" ]]; then
  STOP_AXIS="${2:?usage: run_stage2_gpu.sh --stop <AXIS>}"
  AXIS_DIR="$E8_RUN/${STOP_AXIS}-stage2"
  if [[ -f "$AXIS_DIR/gpu-run.pid" ]]; then
    PGID=$(cat "$AXIS_DIR/gpu-run.pid")
    echo "stopping Stage-2 GPU-run process group $PGID for $STOP_AXIS ..."
    kill -TERM -- "-$PGID" 2>/dev/null || true
    echo "[$(date -u +%FT%TZ)] STOP | run_stage2_gpu $STOP_AXIS (PGID $PGID) | manual --stop" >> "$INTERV" 2>/dev/null || true
    echo "stopped. Re-run to resume (equiv gate + scorer recomputed from banked gens)."
  else
    echo "no gpu-run.pid in $AXIS_DIR"
  fi
  exit 0
fi

AXIS="${AXIS:?set AXIS=A1|A2|A3}"
TASKS="${TASKS:?set TASKS=/path/to/corpus-candidates/<axis>.jsonl}"
GEN_LOG="${GEN_LOG:?set GEN_LOG=~/e8-run/<AXIS>-stage2/stage2-gen.jsonl}"
PRUNED="${PRUNED:-/dev/null}"            # filter-stage pruned-items.json for this axis (or /dev/null)
ARMS="${ARMS:-B}"
THREADS="${THREADS:-2}"
DEVICE="${DEVICE:-mps}"
N_TASKS_SMOKE="${N_TASKS_SMOKE:-}"       # optional: first-N-task cheap pre-gate (separate smoke step)
EQUIV_N_TASKS="${EQUIV_N_TASKS:-}"       # composition gate mode: unset = FULL-axis (conservative
                                         # default, preserved); set N = SHARD gate on first N tasks.
                                         # Shard-gate is an owner/lead THROUGHPUT decision layered on
                                         # the twice-proven (0-flips on this model/corpus class)
                                         # composition gate + the per-axis stratified CPU oracle —
                                         # full-axis double-scores everything (~20 min/axis).
SAMPLE_CAP="${SAMPLE_CAP:-12}"           # oracle sample gate: ~12 stratified tasks/axis (CPU ~3-6 min)

AXIS_DIR="$E8_RUN/${AXIS}-stage2"
mkdir -p "$AXIS_DIR"
LOG="$AXIS_DIR/gpu-run.log"
EQUIV_OUT="$AXIS_DIR/batched-stage2-equiv.json"
SCORES_OUT="$AXIS_DIR/batched-stage2-scores.json"
RESULTS_DIR="$AXIS_DIR/results"          # score_worker-shaped per-task JSONs (verdict input)

[[ -f "$TASKS" ]]   || { echo "TASKS not found: $TASKS" >&2; exit 2; }
[[ -f "$GEN_LOG" ]] || { echo "GEN_LOG not found: $GEN_LOG (run stage2_generate.sh first)" >&2; exit 2; }

run() {
  set -o pipefail
  local rc
  cd "$HARNESS"
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 GPU-SOLO SCORING START (device=$DEVICE) ===" | tee -a "$LOG"

  if [[ -n "$N_TASKS_SMOKE" ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 SMOKE EQUIV GATE (first $N_TASKS_SMOKE tasks) ===" | tee -a "$LOG"
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/batched_stage2_equiv.py" \
      --tasks "$TASKS" --gen-log "$GEN_LOG" --pruned "$PRUNED" \
      --out "$AXIS_DIR/batched-stage2-equiv-smoke.json" --arms "$ARMS" \
      --n-tasks "$N_TASKS_SMOKE" --threads "$THREADS" --device "$DEVICE" 2>&1 | tee -a "$LOG"
    rc="${PIPESTATUS[0]}"
    if [[ "$rc" -ne 0 ]]; then
      echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 SMOKE GATE FAILED (rc=$rc) — ABORT ===" | tee -a "$LOG"
      echo "[$(date -u +%FT%TZ)] ABORT | run_stage2_gpu $AXIS | smoke equiv gate FAILED" >> "$INTERV"
      return 1
    fi
  fi

  # composition gate: FULL-axis (EQUIV_N_TASKS unset) or SHARD (--n-tasks N). Mode recorded in the
  # log + INTERVENTIONS so the verdict record shows which ran.
  equiv_mode="full-axis"
  equiv_shard_flag=""
  if [[ -n "$EQUIV_N_TASKS" ]]; then
    equiv_mode="shard(N=$EQUIV_N_TASKS)"
    equiv_shard_flag="--n-tasks $EQUIV_N_TASKS"
  fi
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 EQUIV GATE ($equiv_mode) ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/batched_stage2_equiv.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --pruned "$PRUNED" \
    --out "$EQUIV_OUT" --arms "$ARMS" --threads "$THREADS" --device "$DEVICE" $equiv_shard_flag 2>&1 | tee -a "$LOG"
  rc="${PIPESTATUS[0]}"
  if [[ "$rc" -ne 0 ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 EQUIV GATE ($equiv_mode) FAILED (rc=$rc) — ABORT before scored pass ===" | tee -a "$LOG"
    echo "[$(date -u +%FT%TZ)] ABORT | run_stage2_gpu $AXIS | equiv gate ($equiv_mode) FAILED (boolean flip); scored pass NOT run" >> "$INTERV"
    return 1
  fi
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 EQUIV GATE PASSED ($equiv_mode, zero flips) — scored pass ===" | tee -a "$LOG"
  echo "[$(date -u +%FT%TZ)] GATE | run_stage2_gpu $AXIS | composition equiv PASSED ($equiv_mode)" >> "$INTERV"

  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 SCORED PASS (batched_stage2_scorer) ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/batched_stage2_scorer.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --pruned "$PRUNED" \
    --out "$SCORES_OUT" --results-dir "$RESULTS_DIR" --arms "$ARMS" \
    --threads "$THREADS" --device "$DEVICE" 2>&1 | tee -a "$LOG"
  rc="${PIPESTATUS[0]}"
  if [[ "$rc" -ne 0 ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 SCORED PASS ERRORED (rc=$rc) ===" | tee -a "$LOG"
    echo "[$(date -u +%FT%TZ)] ERROR | run_stage2_gpu $AXIS | batched_stage2_scorer nonzero exit" >> "$INTERV"
    return 1
  fi

  # step 3: ORACLE SAMPLE GATE (Option C) — bounded stratified fresh-CPU per-task re-score of the GPU
  # results, yielding the real _oracle_result.json the verdict plan §5 reads. oracle_verify.py is
  # byte-unchanged; this wrapper stages a ~SAMPLE_CAP stratified subset and runs it. Any mismatch =
  # loud FAIL, axis verdict BLOCKED, no auto-continue.
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 ORACLE SAMPLE GATE (fresh CPU 1-thread, cap $SAMPLE_CAP) ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/stage2_oracle_sample.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --pruned "$PRUNED" \
    --results-dir "$RESULTS_DIR" --sample-cap "$SAMPLE_CAP" --arms "$ARMS" 2>&1 | tee -a "$LOG"
  rc="${PIPESTATUS[0]}"
  if [[ "$rc" -ne 0 ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 ORACLE SAMPLE GATE FAILED (rc=$rc) — AXIS VERDICT BLOCKED ===" | tee -a "$LOG"
    echo "[$(date -u +%FT%TZ)] FAIL | run_stage2_gpu $AXIS | oracle sample gate MISMATCH; axis verdict blocked — report to lead" >> "$INTERV"
    return 1
  fi
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 ORACLE SAMPLE PASSED (fresh-CPU per-task ==) ===" | tee -a "$LOG"

  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 DONE — equiv=$EQUIV_OUT scores=$SCORES_OUT results=$RESULTS_DIR/ oracle=$RESULTS_DIR/_oracle_result.json ===" | tee -a "$LOG"
  echo "[$(date -u +%FT%TZ)] DONE | run_stage2_gpu $AXIS | equiv PASS + scored pass + oracle sample PASS → $RESULTS_DIR/" >> "$INTERV"
}

# export every var run() references (detached declare -f child does NOT inherit unexported vars)
export DRIVER HARNESS E8_RUN INTERV AXIS TASKS GEN_LOG PRUNED ARMS THREADS DEVICE N_TASKS_SMOKE \
       EQUIV_N_TASKS SAMPLE_CAP AXIS_DIR LOG EQUIV_OUT SCORES_OUT RESULTS_DIR
echo "[$(date -u +%FT%TZ)] LAUNCH | run_stage2_gpu $AXIS (device=$DEVICE, GPU-SOLO) | scoring banked Stage-2 gens; watchers: expected MPS process, do not alarm" >> "$INTERV"
echo "launching $AXIS Stage-2 GPU-solo scoring; log: $LOG"
caffeinate -i nohup bash -c '
  echo $$ > "'"$AXIS_DIR"'/gpu-run.pid"
  '"$(declare -f run)"'
  run
' >/dev/null 2>&1 &
disown
echo "launched (pid $!). Tail: tail -f $LOG   Stop: bash run_stage2_gpu.sh --stop $AXIS"
echo "REMINDER: GPU-SOLO — do NOT launch another model process until this prints DONE."
