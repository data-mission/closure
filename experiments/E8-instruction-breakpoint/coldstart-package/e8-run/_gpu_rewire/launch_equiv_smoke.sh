#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
D=~/e8-run/_gpu_rewire
echo "[$(date -u +%FT%TZ)] LAUNCH | batched_equiv smoke gate (4 fams, mps, batched-vs-per-call, GPU solo) | device gate A_ZERO_FLIPS passed 15:35:17Z; composition gate next" >> ~/e8-run/INTERVENTIONS.log
cd ~/repos/closure/harness
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 nohup caffeinate -i uv run python -u ~/e8-driver/batched_equiv.py \
  --tasks ~/e8-run/_smoke/tasks.jsonl --gen-log ~/e8-run/_smoke/gen.jsonl \
  --families A3-C-0002,A3-C-0003,A3-C-0105,A3-C-0106 \
  --out "$D/equiv-smoke.json" --device mps --threads 2 --n-draws 3 \
  > "$D/equiv-smoke.log" 2>&1 &
echo "$!" > "$D/equiv.pid"
disown -a
echo "LAUNCHED_PID=$(cat $D/equiv.pid)"
