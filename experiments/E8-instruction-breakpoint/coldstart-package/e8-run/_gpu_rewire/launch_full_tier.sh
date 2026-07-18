#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
CORPUS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates
corpus_for() { case "$1" in A3) echo A3-corrections;; A2) echo A2-scoped-exception;; A1) echo A1-depth;; *) echo UNKNOWN; return 1;; esac; }
cd ~/repos/closure/harness
for AXIS in A3 A2 A1; do
  OUT=~/e8-run/$AXIS-filter/batched-scores.json
  LOG=~/e8-run/$AXIS-filter/batched-run.log
  echo "[$(date -u +%FT%TZ)] LAUNCH | batched_scorer $AXIS full axis (mps, fp32, bs=16, GPU solo) | both gates PASSED (device A_ZERO_FLIPS 15:35Z, composition PASS 15:37Z); corpus-gen task_id binding verified" >> ~/e8-run/INTERVENTIONS.log
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u ~/e8-driver/batched_scorer.py \
    --tasks "$CORPUS/$(corpus_for $AXIS).jsonl" --gen-log ~/e8-run/$AXIS-filter/filter-gen.jsonl \
    --out "$OUT" --device mps --threads 2 --n-draws 3 > "$LOG" 2>&1
  echo "[$(date -u +%FT%TZ)] DONE | batched_scorer $AXIS | $(tail -2 "$LOG" | head -1 | cut -c1-200)" >> ~/e8-run/INTERVENTIONS.log
done
echo "[$(date -u +%FT%TZ)] DONE | full filter tier scored on GPU (A3,A2,A1) | all outputs banked" >> ~/e8-run/INTERVENTIONS.log
