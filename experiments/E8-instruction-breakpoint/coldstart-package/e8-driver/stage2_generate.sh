#!/usr/bin/env bash
# =============================================================================
# stage2_generate.sh — E8 STAGE-2 (registered-run) generation for ONE axis.
# =============================================================================
# Generates the Arm-B draws for the FULL corpus of one axis (all dose levels / all families,
# ONE draw per task — not the filter tier's 2-state×3-draw structure). This is the registered-run
# generation that Stage-2 scoring consumes.
#
# SPEND — OWNER-GATED. This spends real API money (~$8.21 total across all three axes for 1,176
# draws). It requires an explicit `--go` flag AND the owner's key file. Without --go it prints the
# plan + cost and does NOT call the API (dry-run equivalent). NEVER launch this unattended without
# the owner's decision to spend.
#
# DRAW COUNTS (verified: corpus-candidates row counts == family-fingerprint run.log counts):
#   A1 → corpus-candidates/A1-depth.jsonl            450 tasks → 450 Arm-B draws
#   A2 → corpus-candidates/A2-scoped-exception.jsonl 390 tasks → 390 Arm-B draws
#   A3 → corpus-candidates/A3-corrections.jsonl      336 tasks → 336 Arm-B draws
#   TOTAL 1,176 draws (matches GPU-REWIRE-NOTES §2 "1,176 draws ≈ $8.21").
# generation_driver.py does ONE generation per (task, arm) with arm=B (no --n-draws), so one draw
# per corpus row. Resumable: a (task_id, arm) already banked clean at the live config_hash is
# skipped (generation_driver.py:160-164).
#
# API KEY — read from ~/.anthropic_key (600 perms) into ANTHROPIC_API_KEY at launch, NEVER echoed,
# NEVER logged, NEVER on the CLI. The frozen provider (providers.py:106) reads ANTHROPIC_API_KEY
# from env on EACH call and never prints it; this script only exports it and immediately unsets its
# local copy. `set +x` is forced so no trace can leak the value.
#
# ARM-B PIN — generation_driver.py enforces the frozen ARM-B instruction hash
# (f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c) at startup and REFUSES to run
# under any other instruction. We pass the pinned file; do NOT pass --allow-unpinned-instruction.
#
# RATE — GPU-REWIRE-NOTES §3d: for Stage-2, raise --rate/--concurrency toward the provider ceiling
# (generation is network-bound; total wall should be dominated by nothing). Defaults here are raised
# vs the filter tier (which used rate 2.0 / 2 threads) but stay conservative; tune RATE/CONCURRENCY
# up if the provider tolerates it. Retries + capped backoff are built into generation_driver.
#
# USAGE (owner runs, on the Mini):
#   # dry plan (no key, no spend):
#   AXIS=A3 \
#   TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
#   bash stage2_generate.sh
#
#   # real generation (spends money — owner only):
#   AXIS=A3 \
#   TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
#   bash stage2_generate.sh --go
#
#   Stop: bash stage2_generate.sh --stop A3
# =============================================================================
set -euo pipefail
set +x                                   # HARD: never trace (protects the key)

export PATH="$HOME/.local/bin:$PATH"     # uv resolves under nohup/caffeinate (launch.sh lesson)

DRIVER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="${CLOSURE_HARNESS:-$HOME/repos/closure/harness}"
E8_RUN="${E8_RUN:-$HOME/e8-run}"
INTERV="$E8_RUN/INTERVENTIONS.log"
KEY_FILE="${KEY_FILE:-$HOME/.anthropic_key}"
TEMPLATE="${TEMPLATE:-$E8_RUN/template.txt}"
ARMB="${ARMB:-$HOME/repos/closure/experiments/E5-reclosure/ARM-B-INSTRUCTION.md}"

# ---- --stop <AXIS> ----
if [[ "${1:-}" == "--stop" ]]; then
  STOP_AXIS="${2:?usage: stage2_generate.sh --stop <AXIS>}"
  AXIS_DIR="$E8_RUN/${STOP_AXIS}-stage2"
  if [[ -f "$AXIS_DIR/gen.pid" ]]; then
    PGID=$(cat "$AXIS_DIR/gen.pid")
    echo "stopping Stage-2 gen process group $PGID for $STOP_AXIS ..."
    kill -TERM -- "-$PGID" 2>/dev/null || true
    echo "[$(date -u +%FT%TZ)] STOP | stage2_generate $STOP_AXIS (PGID $PGID) | manual --stop" >> "$INTERV" 2>/dev/null || true
    echo "stopped. Re-run to resume (banked draws are skipped)."
  else
    echo "no gen.pid in $AXIS_DIR"
  fi
  exit 0
fi

GO=0
[[ "${1:-}" == "--go" ]] && GO=1

# ---- config ----
AXIS="${AXIS:?set AXIS=A1|A2|A3}"
TASKS="${TASKS:?set TASKS=/path/to/corpus-candidates/<axis>.jsonl}"
RATE="${RATE:-4.0}"                      # submissions/sec (raised vs filter's 2.0; tune to ceiling)
CONCURRENCY="${CONCURRENCY:-8}"          # in-flight requests (raised vs filter's 4)
MAX_RETRIES="${MAX_RETRIES:-5}"
BACKOFF_BASE="${BACKOFF_BASE:-1.0}"

AXIS_DIR="$E8_RUN/${AXIS}-stage2"
mkdir -p "$AXIS_DIR"
GEN_LOG="$AXIS_DIR/stage2-gen.jsonl"
LOG="$AXIS_DIR/stage2-gen.log"

# ---- pre-flight existence checks (fail fast, before any spend or detach) ----
[[ -f "$TASKS" ]]     || { echo "TASKS not found: $TASKS" >&2; exit 2; }
[[ -f "$TEMPLATE" ]]  || { echo "TEMPLATE not found: $TEMPLATE" >&2; exit 2; }
[[ -f "$ARMB" ]]      || { echo "ARMB instruction not found: $ARMB" >&2; exit 2; }

N_TASKS=$(grep -c . "$TASKS")

if [[ "$GO" -ne 1 ]]; then
  echo "=== STAGE-2 GENERATION PLAN (dry — no key, no spend) ==="
  echo "  axis:        $AXIS"
  echo "  tasks:       $TASKS  ($N_TASKS rows → $N_TASKS Arm-B draws)"
  echo "  template:    $TEMPLATE"
  echo "  arm-b:       $ARMB (hash-pinned; driver refuses any other instruction)"
  echo "  gen-log:     $GEN_LOG   (resumable; banked draws skipped)"
  echo "  rate/conc:   $RATE/s, $CONCURRENCY in-flight"
  echo "  key file:    $KEY_FILE (read at launch, never logged)  [absent in dry mode]"
  echo
  echo "To actually generate (SPENDS ~\$$(python3 -c "print(round($N_TASKS/1176*8.21,2))") for this axis), re-run with --go and the key file present."
  echo "Verify plumbing with zero spend first via the harness dry-run in README-RUN.md if unsure."
  exit 0
fi

# ---- --go path: OWNER SPEND ----
[[ -f "$KEY_FILE" ]] || { echo "key file not found: $KEY_FILE (owner must place it, 600 perms)" >&2; exit 3; }
# refuse a world-readable key (defensive; the owner's file should be 600)
PERM=$(stat -f "%Lp" "$KEY_FILE" 2>/dev/null || stat -c "%a" "$KEY_FILE" 2>/dev/null || echo "")
if [[ -n "$PERM" && "$PERM" != "600" ]]; then
  echo "WARNING: $KEY_FILE perms are $PERM, expected 600. Refusing to read a non-600 key." >&2
  exit 3
fi

# read key into env WITHOUT echoing; keep it only in the exported var, unset the local immediately
ANTHROPIC_API_KEY="$(cat "$KEY_FILE")"
export ANTHROPIC_API_KEY
[[ -n "$ANTHROPIC_API_KEY" ]] || { echo "key file is empty: $KEY_FILE" >&2; exit 3; }

# the work function — runs detached; references exported vars (see export list below)
run() {
  set -o pipefail
  set +x                                 # belt-and-suspenders inside the child too
  cd "$HARNESS"
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 GENERATION START ($N_TASKS Arm-B draws, rate=$RATE, conc=$CONCURRENCY) ===" | tee -a "$LOG"
  # NOTE: no --dry-run; the key is in env; generation_driver reads it per call and never logs it.
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u "$DRIVER/generation_driver.py" \
    --tasks "$TASKS" --gen-log "$GEN_LOG" --arms B \
    --template "$TEMPLATE" --arm-b-instruction "$ARMB" \
    --concurrency "$CONCURRENCY" --rate "$RATE" \
    --max-retries "$MAX_RETRIES" --backoff-base "$BACKOFF_BASE" 2>&1 | tee -a "$LOG"
  local rc="${PIPESTATUS[0]}"
  if [[ "$rc" -ne 0 ]]; then
    echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 GENERATION ERRORED (rc=$rc) ===" | tee -a "$LOG"
    echo "[$(date -u +%FT%TZ)] ERROR | stage2_generate $AXIS | generation_driver nonzero exit" >> "$INTERV"
    return 1
  fi
  echo "=== [$(date -u +%FT%TZ)] $AXIS STAGE-2 GENERATION DONE — banked → $GEN_LOG ===" | tee -a "$LOG"
  echo "[$(date -u +%FT%TZ)] DONE | stage2_generate $AXIS | $N_TASKS Arm-B draws banked → $GEN_LOG" >> "$INTERV"
}

# export every var run() references so the detached declare -f child sees them (the trap: declare -f
# serializes function TEXT; vars resolve at run-time in the child, which does NOT inherit unexported
# shell vars — proven in run_axis_gpu.sh review). ANTHROPIC_API_KEY is already exported above.
export DRIVER HARNESS E8_RUN INTERV AXIS TASKS TEMPLATE ARMB RATE CONCURRENCY MAX_RETRIES \
       BACKOFF_BASE AXIS_DIR GEN_LOG LOG N_TASKS

echo "[$(date -u +%FT%TZ)] LAUNCH | stage2_generate $AXIS (SPEND, $N_TASKS Arm-B draws) | owner-gated generation; watchers: expected API traffic, do not alarm" >> "$INTERV"
echo "launching $AXIS Stage-2 generation (SPENDING); log: $LOG"
caffeinate -i nohup bash -c '
  echo $$ > "'"$AXIS_DIR"'/gen.pid"
  '"$(declare -f run)"'
  run
' >/dev/null 2>&1 &
disown
echo "launched (pid $!). Tail: tail -f $LOG   Stop: bash stage2_generate.sh --stop $AXIS"
