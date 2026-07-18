#!/usr/bin/env bash
# GPU-rewire smoke probe launcher — 2026-07-18. Strict MPS (no PYTORCH_ENABLE_MPS_FALLBACK):
# unsupported ops RAISE instead of silently running on CPU. threads=2 matches serial_gt numerics.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
D=~/e8-run/_gpu_rewire
echo "[$(date -u +%FT%TZ)] LAUNCH | gpu_probe smoke (4 fams, strict-MPS, threads=2, GPU solo) | owner-authorized GPU rewire, ceremony dropped; watchers: expected process" >> ~/e8-run/INTERVENTIONS.log
cd ~/repos/closure/harness
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 nohup caffeinate -i uv run python -u ~/e8-driver/gpu_probe.py \
  --tasks ~/e8-run/_smoke/tasks.jsonl --gen-log ~/e8-run/_smoke/gen.jsonl \
  --cpu-gt ~/e8-run/_smoke/serial_gt.json \
  --families A3-C-0002,A3-C-0003,A3-C-0105,A3-C-0106 \
  --out "$D/probe-smoke.json" --threads 2 --n-draws 3 \
  > "$D/probe-smoke.log" 2>&1 &
PID=$!
echo "$PID" > "$D/probe.pid"
nohup bash -c "while kill -0 $PID 2>/dev/null; do printf \"[%s] %s cpu=%s%%\n\" \"\$(date -u +%FT%TZ)\" \"\$(ioreg -r -d 1 -w 0 -c IOAccelerator 2>/dev/null | grep -o '\"Device Utilization %\"=[0-9]*' | head -1)\" \"\$(ps -o %cpu= -p $PID | tr -d \" \")\"; sleep 5; done" > "$D/gpu-util.log" 2>&1 &
disown -a
echo "LAUNCHED_PID=$PID"
