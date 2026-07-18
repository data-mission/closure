#!/usr/bin/env bash
# =============================================================================
# run_axis_gpu.sh — E8 filter-tier GPU (MPS) SCORING for ONE axis, gated + solo.
# =============================================================================
# Scores the BANKED filter generations for one axis on Apple MPS in two steps:
#   1. batched_equiv.py   — full-axis equivalence gate (batched vs per-call, SAME device).
#                           EXIT-CHECKED: nonzero (a boolean flipped) ABORTS before any scored pass.
#   2. batched_scorer.py  — the scored pass (fixed canonical batches), only if the gate PASSED.
#
# GPU-SOLO RULE (memory, GPU-REWIRE-NOTES §1): GPU scoring runs with NO concurrent CPU scorer fleet
# and ONE model process at a time. Do NOT launch two axes' run_axis_gpu.sh concurrently — they would
# co-run two DeBERTa-large instances on 16GB unified memory and drive swap. Run axes SEQUENTIALLY.
#
# Nothing here generates or spends API: scoring only, banked gens, no key needed, no freeze gate
# (scoring produces no new registered data — same rule as run_e5 --score-only). Certification order
# still stands: gpu_probe (device gate, Step Zero) must have PASSED for this axis's corpus/model
# BEFORE trusting these numbers; batched_equiv here is the composition gate on top of that.
#
# Survives sleep/logout: caffeinate -i + nohup, own process group, run.pid for --stop.
# Progress → <axis-dir>/gpu-run.log (timestamped tee). INTERVENTIONS.log gets LAUNCH/DONE entries.
#
# USAGE:
#   AXIS=A3 \
#   TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
#   GEN_LOG=~/e8-run/A3-filter/filter-gen.jsonl \
#   bash run_axis_gpu.sh
#
#   Stop:  bash run_axis_gpu.sh --stop A3       (kills the process group for that axis)
#
# The per-axis TASKS path is FIXED provenance (verified against the run.log family fingerprints
# 150/130/112 — see BATCHED-NOTES / readiness report):
#   A1 → corpus-candidates/A1-depth.jsonl            (150 families, 900 draws)
#   A2 → corpus-candidates/A2-scoped-exception.jsonl (130 families, 780 draws)
#   A3 → corpus-candidates/A3-corrections.jsonl      (112 families, 672 draws)
# Each axis's filter stage consumed its RAW corpus-candidate file directly (no derived tasks file).
# =============================================================================
set -euo pipefail

# ---- ops trap #1: PATH prefix so `uv` resolves under nohup/caffeinate (launch.sh lesson) ----
export PATH="$HOME/.local/bin:$PATH"

DRIVER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="${CLOSURE_HARNESS:-$HOME/repos/closure/harness}"
E8_RUN="${E8_RUN:-$HOME/e8-run}"
INTERV="$E8_RUN/INTERVENTIONS.log"

# ---- --stop <AXIS> ----
if [[ "${1:-}" == "--stop" ]]; then
  STOP_AXIS="${2:?usage: run_axis_gpu.sh --stop <AXIS e.g. A3>}"
  AXIS_DIR="$E8_RUN/${STOP_AXIS}-filter"
  if [[ -f "$AXIS_DIR/gpu-run.pid" ]]; then
    PGID=$(cat "$AXIS_DIR/gpu-run.pid")
    echo "stopping GPU-run process group $PGID for $STOP_AXIS ..."
    kill -TERM -- "-$PGID" 2>/dev/null || true
    echo "[$(date -u +%FT%TZ)] STOP | run_axis_gpu $STOP_AXIS (PGID $PGID) | manual --stop" >> "$INTERV" 2>/dev/null || true
    echo "stopped. Re-run to resume (equiv gate + scorer are recomputed from banked gens)."
  else
    echo "no gpu-run.pid in $AXIS_DIR"
  fi
  exit 0
fi

# ---- config ----
AXIS="${AXIS:?set AXIS=A1|A2|A3}"
TASKS="${TASKS:?set TASKS=/path/to/corpus-candidates/<axis>.jsonl}"
GEN_LOG="${GEN_LOG:?set GEN_LOG=~/e8-run/<AXIS>-filter/filter-gen.jsonl}"
N_DRAWS="${N_DRAWS:-3}"
THREADS="${THREADS:-2}"
DEVICE="${DEVICE:-mps}"
SMOKE_FAMILIES="${SMOKE_FAMILIES:-}"   # optional: comma-separated family ids for a cheap pre-gate

AXIS_DIR="$E8_RUN/${AXIS}-filter"
mkdir -p "$AXIS_DIR"
LOG="$AXIS_DIR/gpu-run.log"
EQUIV_OUT="$AXIS_DIR/batched-equiv.json"
SCORES_OUT="$AXIS_DIR/batched-scores.json"

# fail fast on obviously-wrong inputs BEFORE detaching (cheap, surfaces typos immediately)
[[ -f "$TASKS" ]]   || { echo "TASKS not found: $TASKS" >&2; exit 2; }
[[ -f "$GEN_LOG" ]] || { echo "GEN_LOG not found: $GEN_LOG" >&2; exit 2; }

# ---- the work function (declared, then run inside the detached shell) ----
run() {
  cd "$HARNESS"
  # pipefail so ${PIPESTATUS[0]} reflects python's exit through `| tee`; the detached bash -c does
  # NOT inherit the outer set -euo, so set it here. We deliberately do NOT set -e inside run(): an
  # abort must still write its INTERVENTIONS.log line and `return 1`, not die silently mid-pipe.
  set -o pipefail
  local rc

  echo "=== [$(date -u +%FT%TZ)] $AXIS GPU-SOLO SCORING START (device=$DEVICE, tasks=$TASKS) ===" | tee -a "$LOG"

  # optional cheap shard pre-gate (fast confidence before the full-axis gate)
  if [[ -n "$SMOKE_FAMILIES" ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS SMOKE EQUIV GATE (families=$SMOKE_FAMILIES) ===" | tee -a "$LOG"
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/batched_equiv.py" \
      --tasks "$TASKS" --gen-log "$GEN_LOG" --out "$AXIS_DIR/batched-equiv-smoke.json" \
      --n-draws "$N_DRAWS" --threads "$THREADS" --device "$DEVICE" \
      --families "$SMOKE_FAMILIES" 2>&1 | tee -a "$LOG"
    rc="${PIPESTATUS[0]}"   # capture IMMEDIATELY — python's exit, not tee's; volatile, grab it now
    if [[ "$rc" -ne 0 ]]; then
      echo "=== [$(date -u +%FT%TZ)] $AXIS SMOKE GATE FAILED (rc=$rc) — ABORT (no full gate, no scored pass) ===" | tee -a "$LOG"
      echo "[$(date -u +%FT%TZ)] ABORT | run_axis_gpu $AXIS | smoke equiv gate FAILED (boolean flip)" >> "$INTERV"
      return 1
    fi
  fi

  # full-axis equivalence gate (batched vs per-call, same device) — EXIT-CHECKED
  echo "=== [$(date -u +%FT%TZ)] $AXIS FULL EQUIV GATE ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/batched_equiv.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --out "$EQUIV_OUT" \
    --n-draws "$N_DRAWS" --threads "$THREADS" --device "$DEVICE" 2>&1 | tee -a "$LOG"
  rc="${PIPESTATUS[0]}"
  if [[ "$rc" -ne 0 ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS FULL EQUIV GATE FAILED (rc=$rc) — ABORT before scored pass ===" | tee -a "$LOG"
    echo "[$(date -u +%FT%TZ)] ABORT | run_axis_gpu $AXIS | full equiv gate FAILED (boolean flip); scored pass NOT run" >> "$INTERV"
    return 1
  fi
  echo "=== [$(date -u +%FT%TZ)] $AXIS EQUIV GATE PASSED (zero flips) — proceeding to scored pass ===" | tee -a "$LOG"

  # scored pass — only reached on a PASSED gate
  echo "=== [$(date -u +%FT%TZ)] $AXIS SCORED PASS (batched_scorer) ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/batched_scorer.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --out "$SCORES_OUT" \
    --n-draws "$N_DRAWS" --threads "$THREADS" --device "$DEVICE" 2>&1 | tee -a "$LOG"
  rc="${PIPESTATUS[0]}"
  if [[ "$rc" -ne 0 ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS SCORED PASS ERRORED (rc=$rc) ===" | tee -a "$LOG"
    echo "[$(date -u +%FT%TZ)] ERROR | run_axis_gpu $AXIS | batched_scorer nonzero exit" >> "$INTERV"
    return 1
  fi

  echo "=== [$(date -u +%FT%TZ)] $AXIS DONE — equiv=$EQUIV_OUT scores=$SCORES_OUT ===" | tee -a "$LOG"
  echo "[$(date -u +%FT%TZ)] DONE | run_axis_gpu $AXIS | equiv PASS + scored pass complete → $SCORES_OUT" >> "$INTERV"
}

# ---- launch: caffeinate keeps the Mini awake; nohup detaches; own PGID for --stop ----
# `declare -f run` serializes the function TEXT; its $LOG/$INTERV/$AXIS/$DRIVER/$TASKS/… are resolved
# at run-time INSIDE the detached `bash -c`, which does NOT inherit shell vars unless exported. Export
# every var run() references so the child shell sees them (without this, they'd be empty → tee writes
# to "" and paths break). This is the subtle trap that makes a detached declare-f function silently
# no-op; export is the fix.
export DRIVER HARNESS E8_RUN INTERV AXIS TASKS GEN_LOG N_DRAWS THREADS DEVICE SMOKE_FAMILIES \
       AXIS_DIR LOG EQUIV_OUT SCORES_OUT
echo "[$(date -u +%FT%TZ)] LAUNCH | run_axis_gpu $AXIS (device=$DEVICE, GPU-SOLO) | scoring banked gens; watchers: expected MPS process, do not alarm" >> "$INTERV"
echo "launching $AXIS GPU-solo scoring; log: $LOG"
caffeinate -i nohup bash -c '
  echo $$ > "'"$AXIS_DIR"'/gpu-run.pid"
  '"$(declare -f run)"'
  run
' >/dev/null 2>&1 &
disown
echo "launched (pid $!). Tail: tail -f $LOG   Stop: bash run_axis_gpu.sh --stop $AXIS"
echo "REMINDER: GPU-SOLO — do NOT launch another axis until this one prints DONE (one model process at a time)."
