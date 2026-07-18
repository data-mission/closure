#!/usr/bin/env bash
# =============================================================================
# launch.sh — E8 corpus run launcher for the Mac Mini (M4, 4P+6E, 16GB)
# =============================================================================
# ONE command. Runs, in order, for one axis:
#   1. generation_driver.py  — Arm-B generations for every probe task (concurrent, rate-bound).
#   2. calibrate_and_run.py  — 10-min calibration → worker autotune → parallel scoring to done.
#   3. oracle_verify.py      — per-task == oracle in a fresh 1-thread process (FAILS LOUD).
#
# Survives sleep/logout: `caffeinate -i` prevents idle sleep; `nohup` detaches from the shell.
# Progress goes to run.log; check with `tail -f <axis-dir>/run.log`.
#
# API KEY: export ANTHROPIC_API_KEY before launching (generation only). NEVER passed on the CLI,
# NEVER logged. Scoring + oracle need no key. Use --dry-run to verify plumbing with no key/spend.
#
# STOP: `bash launch.sh --stop <axis-dir>` (kills the process group). Resume by re-running the
# same command — generation, scoring, and oracle are all resumable (banked rows / result files).
#
# softwareupdate deferral (documented, Vlad runs if desired, optional): a long unattended run can
# be interrupted by an OS auto-update restart. To defer during the run:
#     sudo softwareupdate --schedule off        # disable automatic checks for the run
#     # ... run ...
#     sudo softwareupdate --schedule on         # re-enable afterwards
# (Requires admin; the driver itself never touches system settings.)
# =============================================================================
set -euo pipefail

DRIVER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="${CLOSURE_HARNESS:-$HOME/repos/closure/harness}"

if [[ "${1:-}" == "--stop" ]]; then
  AXIS_DIR="${2:?usage: launch.sh --stop <axis-dir>}"
  if [[ -f "$AXIS_DIR/run.pid" ]]; then
    PGID=$(cat "$AXIS_DIR/run.pid")
    echo "stopping process group $PGID ..."
    kill -TERM -- "-$PGID" 2>/dev/null || true
    echo "stopped. Re-run launch.sh to resume."
  else
    echo "no run.pid in $AXIS_DIR"
  fi
  exit 0
fi

# ---- config ----
AXIS_DIR="${AXIS_DIR:?set AXIS_DIR=/path/to/axis-work-dir}"
TASKS="${TASKS:?set TASKS=/path/to/tasks.jsonl}"
TEMPLATE="${TEMPLATE:?set TEMPLATE=/path/to/prompt_template.txt}"
ARMB="${ARMB:?set ARMB=/path/to/ARM-B-INSTRUCTION.md}"
PRUNED="${PRUNED:-/dev/null}"
ARMS="${ARMS:-B}"
THREADS="${THREADS:-2}"
CONFIG_HASH="${CONFIG_HASH:-}"           # optional: abort scoring if live hash differs
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$AXIS_DIR"/{gen,results,locks}
GEN_LOG="$AXIS_DIR/gen/gen-log.jsonl"
LOG="$AXIS_DIR/run.log"

dry_flag=""; [[ "$DRY_RUN" == "1" ]] && dry_flag="--dry-run"
ch_flag=""; [[ -n "$CONFIG_HASH" ]] && ch_flag="--config-hash $CONFIG_HASH"

run() {
  cd "$HARNESS"
  echo "=== [$(date -u +%FT%TZ)] GENERATION ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/generation_driver.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --arms "$ARMS" \
    --template "$TEMPLATE" --arm-b-instruction "$ARMB" $dry_flag 2>&1 | tee -a "$LOG"

  echo "=== [$(date -u +%FT%TZ)] CALIBRATE + SCORE ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/calibrate_and_run.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --pruned "$PRUNED" \
    --out-dir "$AXIS_DIR/results" --lock-dir "$AXIS_DIR/locks" \
    --threads "$THREADS" --arms "$ARMS" $ch_flag 2>&1 | tee -a "$LOG"

  echo "=== [$(date -u +%FT%TZ)] ORACLE (per-task ==, fresh 1-thread) ===" | tee -a "$LOG"
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/oracle_verify.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --pruned "$PRUNED" \
    --out-dir "$AXIS_DIR/results" --arms "$ARMS" 2>&1 | tee -a "$LOG"
  echo "=== [$(date -u +%FT%TZ)] DONE — oracle verdict above; results in $AXIS_DIR/results ===" \
    | tee -a "$LOG"
}

# detach: caffeinate keeps the Mini awake; nohup + setsid-style new process group for --stop
echo "launching E8 run for $AXIS_DIR (dry_run=$DRY_RUN); log: $LOG"
caffeinate -i nohup bash -c '
  echo $$ > "'"$AXIS_DIR"'/run.pid"
  '"$(declare -f run)"'
  run
' >/dev/null 2>&1 &
disown
echo "launched (pid $!). Tail: tail -f $LOG   Stop: bash launch.sh --stop $AXIS_DIR"
