# READINESS-NOTES — next-phase launch commands, pre-verified (E5 re-anchor + full-axis GPU run)

Command-authoring + local verification only. Nothing was run on the Mini. Two deliverables:
(1) E5 re-anchor readiness (board #4), (2) full-axis run staging (`run_axis_gpu.sh`, board #7).

New files authored (next to the batched deliverables, in this dir):
- `reanchor_e5_mps.py` — E5 re-anchor scorer (score-only, gateless, MPS device override).
- `run_axis_gpu.sh` — per-axis full-tier GPU-solo scoring driver (equiv gate → scored pass).

================================================================================
## 1. E5 RE-ANCHOR READINESS (board #4)

### 1.1 What "re-anchor" means here
Re-score the SAME banked E5 arm generations (A/B/C) on the certified MPS instrument, so the E5
baseline is expressed on the SAME device as the E8-GPU results (preserves the E5↔E8 comparison).
NO generation, NO API spend, NO freeze gate (produces no new registered data — same rule as
`run_e5.py --score-only`, run_e5.py:1107-1112).

### 1.2 BLOCKER FOUND — plain `run_e5.py --score-only` on MPS scores ZERO records
Two facts, both verified locally:
- The banked E5 log (`arms-log.jsonl`) carries the **CPU** config_hash `6dbe47a8e843…`
  (verified: `config_hash()` on this frozen config == `6dbe47a8e843ec1540f64ed6ddd8339c17b95688…`).
- On MPS, `config_hash()` becomes `c7be2036…` (device is a FROZEN field, config.py:36; verified via
  `dataclasses.replace(CONFIG.nli, device="mps")`).
- `run_e5.score_from_log` filters banked records by `rec.config_hash == config_hash()`
  (run_e5.py:549). Run under MPS, the live hash `c7be2036…` ≠ banked `6dbe47a8…` → **zero records
  selected → nothing scored.**
- `run_e5.py` also has no device flag and calls `use_deterministic_algorithms(True)` unconditionally
  (nli.py:62) — which can hard-fail on MPS.

Therefore the re-anchor is NOT a turn-key `run_e5.py --score-only`. It needs a thin device-override
wrapper — `reanchor_e5_mps.py` — which:
- builds the frozen `NLIScorer` on MPS via the SAME monkeypatch `gpu_probe.build_mps_scorer` uses
  (gpu_probe.py:54-84), recording whether warn_only was needed;
- **REUSES run_e5's scoring/stats verbatim** — `load_tasks`, `load_pruned_index`, `read_log`,
  `score_from_log`, `compute_stats`, `verdict_numbers_md`, `_scores_payload` (all confirmed present
  with the exact signatures called);
- passes the **banked (CPU) config_hash** as the `current_config_hash` to `score_from_log`, so record
  selection keys on the generation identity (unchanged) while only the SCORER device moves to GPU.
  This is the same "hold generation fixed, vary only the instrument" discipline as gpu_probe
  (device-only) and batched_scorer (composition-only);
- emits a DELTA block vs the banked CPU `results-summary.json`: per-arm pooled-contamination +
  mean-completeness deltas, and whether any pairwise z-test verdict FLIPPED. Zero flips ⇒ the E5↔E8
  chain holds on the MPS instrument.

### 1.3 Assets — ALL committed at HEAD, reachable on the Mini via `git pull` (nothing to scp)
Verified with `git cat-file -e HEAD:<path>` on branch `e8-run-apparatus` (HEAD 50943187):
- corpus:          `experiments/E5-reclosure/corpus/tasks.jsonl` (60 tasks) — committed ✓
- banked arms-log: `results/E5-reclosure/2026-07-15-registered-run/artifacts/arms-log.jsonl`
  (180 rows = 60×A/B/C, A+B = 120 gen rows) — committed ✓
- prune register:  `results/E5-reclosure/2026-07-15-registered-run/artifacts/pruned-items.json` — committed ✓
- delta baseline:  `results/E5-reclosure/2026-07-15-registered-run/artifacts/results-summary.json` — committed ✓
CAVEAT: `reanchor_e5_mps.py` itself is uncommitted (same as the batched files) — it must be staged on
the Mini by the same mechanism used for batched_scorer/batched_equiv. And the Mini's closure checkout
must be at a commit that CONTAINS these E5 artifacts (they exist on `e8-run-apparatus`; confirm the
Mini is on a branch/commit that has `results/E5-reclosure/…` before relying on `git pull`).

### 1.4 EXACT Mini command (E5 re-anchor)
```
cd ~/repos/closure/harness && PATH="$HOME/.local/bin:$PATH" \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  uv run python -u ~/e8-driver/reanchor_e5_mps.py \
    --corpus ~/repos/closure/experiments/E5-reclosure/corpus/tasks.jsonl \
    --arms-log ~/repos/closure/results/E5-reclosure/2026-07-15-registered-run/artifacts/arms-log.jsonl \
    --pruned-items ~/repos/closure/results/E5-reclosure/2026-07-15-registered-run/artifacts/pruned-items.json \
    --banked-summary ~/repos/closure/results/E5-reclosure/2026-07-15-registered-run/artifacts/results-summary.json \
    --out-dir ~/e8-run/E5-reanchor-mps --device mps
```
- Runtime: **minutes** — 60 tasks × 3 arms; Arm C is contraction (may add NLI calls inside
  `contract()`), but the whole E5 tier is far smaller than one E8 axis (which is ~11 s/family × 112).
  Expect single-digit minutes on MPS. (Unmeasured — the run prints `elapsed_s`.)
- Output: `~/e8-run/E5-reanchor-mps/e5-reanchor-mps-summary.json` (+ `…VERDICT-numbers.md`). The
  summary's `delta_vs_banked_cpu.chain_holds` is the go/no-go signal.
- Zero spend, no freeze gate (score-only).
- PRE-REQ: the MPS instrument should already be **device-certified** (gpu_probe zero-flip, Step Zero)
  before trusting this re-anchor — same instrument, same certification.

================================================================================
## 2. FULL-AXIS RUN READINESS (board #7)

### 2.1 `--tasks` provenance PER AXIS — verified, not assumed
Each axis's filter stage consumed its **RAW `corpus-candidates/*.jsonl` directly** — there is NO
derived/prepared tasks file (confirmed: `filter_stage_progress.py:229` / `filter_parallel.py:242-243`
read `--tasks` verbatim then call `top_level_per_family`; the only files written are outputs). The
per-axis file is pinned by the family-count fingerprint in each `run.log`, cross-checked locally:

| Axis | `--tasks` file (corpus-candidates/) | rows | unique family_id | run.log fingerprint |
|---|---|---|---|---|
| A1 | `A1-depth.jsonl`            | 450 | **150** | `[filter-gen] 900 draws … (150 families × 2 × 3)` |
| A2 | `A2-scoped-exception.jsonl` | 390 | **130** | `[filter-gen] 780 draws … (130 families × 2 × 3)` |
| A3 | `A3-corrections.jsonl`      | 336 | **112** | `[filter-gen] 672 draws … (112 families × 2 × 3)` |

Every file has `family_id`/`task_id`/`must_change`/`axis_params` and the correct `axis` value, and
(correctly) lacks `filter_state` (that is a gen-log field). Absolute path root on the Mini:
`~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/`. Banked gen-logs:
`~/e8-run/<AXIS>-filter/filter-gen.jsonl` (2,352 draws total: 900+780+672).
Negative result: NO log line prints the literal `--tasks` invocation; provenance rests on the
family-count fingerprint (a stronger structural proof — no other corpus produces these counts). The
`_smoke/tasks.jsonl` (12 rows, all A3) is a decoy equivalence-sandbox subset, NOT a real axis input.

### 2.2 `run_axis_gpu.sh` — what it does
Per axis, SEQUENTIALLY (GPU-solo): (1) optional cheap smoke equiv gate on `SMOKE_FAMILIES`;
(2) full-axis `batched_equiv.py` gate (batched vs per-call, same device) — EXIT-CHECKED, a nonzero
exit (boolean flip) ABORTS before any scored pass; (3) `batched_scorer.py` scored pass, only on a
PASSED gate. Traps baked in:
- **PATH prefix** `export PATH="$HOME/.local/bin:$PATH"` (launch.sh lesson: `uv` must resolve under
  nohup/caffeinate).
- **HF offline env** on every `uv run` (`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`).
- **INTERVENTIONS.log** LAUNCH / DONE / ABORT / ERROR entries (watchers must not alarm on the
  expected MPS process).
- **Timestamped tee logs** → `~/e8-run/<AXIS>-filter/gpu-run.log`.
- **`caffeinate -i nohup`** detach + `gpu-run.pid` (process-group) + `--stop <AXIS>`.
- **GPU-SOLO** comment + reminder: ONE model process at a time; do NOT run two axes concurrently
  (16GB unified memory rule, GPU-REWIRE-NOTES §1). Run A1 → A2 → A3 sequentially.
- Pre-detach existence checks on `$TASKS` and `$GEN_LOG` (surface typos immediately, not 3 hours in).
- Exit-code discipline: `set -o pipefail` inside the work fn + `rc="${PIPESTATUS[0]}"` captured on the
  line immediately after each `| tee`, so python's exit (not tee's) drives the abort.

### 2.3 EXACT Mini commands (full-axis, run SEQUENTIALLY — GPU-solo)
```
# A3 first (smallest / already had the most scoring attempts), then A2, then A1:
AXIS=A3 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
GEN_LOG=~/e8-run/A3-filter/filter-gen.jsonl \
bash ~/e8-driver/run_axis_gpu.sh
# tail: tail -f ~/e8-run/A3-filter/gpu-run.log    stop: bash ~/e8-driver/run_axis_gpu.sh --stop A3

# after A3 prints DONE:
AXIS=A2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A2-scoped-exception.jsonl \
GEN_LOG=~/e8-run/A2-filter/filter-gen.jsonl \
bash ~/e8-driver/run_axis_gpu.sh

# after A2 prints DONE:
AXIS=A1 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth.jsonl \
GEN_LOG=~/e8-run/A1-filter/filter-gen.jsonl \
bash ~/e8-driver/run_axis_gpu.sh
```
Optional cheap pre-gate on any axis: add `SMOKE_FAMILIES=<fam1,fam2,fam3,fam4>` to the env.
Outputs per axis: `~/e8-run/<AXIS>-filter/batched-equiv.json` (gate) + `batched-scores.json` (scores).
Runtime per axis: the equiv gate scores BOTH paths (~2× a single pass); single-stream MPS is
~11 s/family, so a full-axis gate is roughly 2 × (families × 11 s) and the scored pass adds one more
batched pass — order of tens of minutes per axis at worst, minutes if batching hits 20–60 pairs/s.
Measured numbers print in each tool's meta/RESULT line.

### 2.4 Certification chain (must hold before trusting scored output)
gpu_probe zero-flip (device gate, Step Zero) → batched_equiv zero-flip per axis (composition gate,
enforced inside run_axis_gpu.sh) → scored pass. The script enforces the second link; the first is the
Step-Zero certification and must already be green for this corpus/model.

================================================================================
## 3. Verification performed locally (no Mini execution)
- `reanchor_e5_mps.py`: ast/syntax OK; all 7 reused `run_e5` functions confirmed present with exact
  called signatures; CPU-vs-MPS config_hash divergence reproduced (`6dbe47a8…` vs `c7be2036…`);
  banked `arms-log.jsonl` confirmed CPU-hash-stamped, 180 rows, no `error` field (handled via
  `.get("error")` in run_e5).
- `run_axis_gpu.sh`: `bash -n` clean; end-to-end behavioral test with STUBBED batched_equiv/scorer +
  fake `uv`/`caffeinate` proved BOTH paths — PASS: gate→scored-pass→DONE (+INTERVENTIONS DONE);
  FAIL: gate rc=1 → ABORT, scored pass NEVER ran (+INTERVENTIONS ABORT). Fixed two real shell bugs
  found in hostile review: (a) `${PIPESTATUS[0]}` must be captured immediately after the pipe (done);
  (b) the detached `declare -f run` child does NOT inherit shell vars — every var run() references is
  now `export`ed before launch (without this the detached fn silently no-ops with empty paths).
- `--tasks` provenance: family counts 150/130/112 independently recomputed and matched to run.log.
- E5 assets: all four committed at HEAD (reachable via git pull, no scp).

### Things still to confirm on the Mini (cannot verify locally)
- The uncommitted new files (`reanchor_e5_mps.py`, `run_axis_gpu.sh`) must be staged on the Mini
  (same as batched_scorer/batched_equiv).
- The Mini's closure checkout must be on a commit that contains `results/E5-reclosure/…` for the E5
  `git pull` reachability to hold.
- Real runtimes + real pairs/s are unmeasured (tools print them).
- Step-Zero device certification (gpu_probe) must be green before either phase's numbers are trusted.
