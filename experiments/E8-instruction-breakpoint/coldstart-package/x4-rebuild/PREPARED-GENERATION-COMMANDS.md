# X4 — PREPARED generation + scoring commands (NOT launched; owner fires with disclosure)

Zero-spend until the owner runs these with `--go` and the key file present. All paths assume the Mini
layout (`~/repos/closure/...`, `~/e8-run/...`, `~/e8-driver/...`) mirroring the registered E8 run.
The transformed corpus must first be copied to the Mini corpus dir.

Cost model: registered run = $8.21 / 1,176 draws = **$0.006981 / draw** (GPU-REWIRE-NOTES §2).

---

## 0. Stage the corpus on the Mini

```bash
# from the repo (local), push the transformed corpus to the Mini
scp experiments/E8-instruction-breakpoint/coldstart-package/x4-rebuild/A1-depth-v2.jsonl \
    mac:~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl
```

447 records (149 families × 3 doses; A1-D-0008 dropped — 3 records rejected at construction, see NOTES).

---

## 1. FILTER TIER — A-dependency filter generation + scoring (894 draws → $6.24)

The filter tier draws the top-level (max-dose = D3) record per family × 2 states (correction /
assumption) × 3 draws. v2 has 149 D3 families (verified: `top_level_per_family` picks all 149),
so 149 × 2 × 3 = **894 draws → $6.24**.

**VERIFIED ENTRY POINT (gates the $6.24 launch):** the filter-gen `filter-gen.jsonl` shape — rows
tagged with `filter_state` ("assumption"|"correction") and `draw_index` — is produced by
`filter_stage.py`, NOT by `stage2_generate.sh` (which does single Arm-B draws). `filter_stage.py`
GENERATES the 2-state×3-draw structure (`run_filter_generation`, filter_stage.py:60-96, calling
`generation_driver.generate_one` under the pinned Arm-B guard) AND CPU-scores + writes the pruning
register in one command. Its CLI (filter_stage.py:196-210): `--tasks --gen-log --out-dir --template
--arm-b-instruction [--n-draws 3] [--rate 2.0] [--dry-run]`. The Arm-B instruction hash pin
(`f9c242…`) is enforced; pass the pinned file, NOT `--allow-unpinned-instruction`. The GPU path
(`run_axis_gpu.sh`) then RE-scores the same banked `filter-gen.jsonl` for the certified numbers.

DRY PLAN (no key, no spend — fake provider; always run first and read the plan):
```bash
ssh mac
cd ~/e8-driver
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -u filter_stage.py \
  --tasks   ~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
  --gen-log ~/e8-run/A1V2-filter/filter-gen.jsonl \
  --out-dir ~/e8-run/A1V2-filter \
  --template ~/e8-run/template.txt \
  --arm-b-instruction ~/repos/closure/experiments/E5-reclosure/ARM-B-INSTRUCTION.md \
  --n-draws 3 --dry-run
# expect: "[filter] ... (149 families × 2 states × 3 draws) ..." then a RESULT line, NO spend.
```

REAL generation (owner only, spends ~$6.24 — export the key first, never on the CLI):
```bash
ssh mac
cd ~/e8-driver
export ANTHROPIC_API_KEY="$(cat ~/.anthropic_key)"      # 600-perm key file; never echoed/logged
caffeinate -i nohup setsid uv run python -u filter_stage.py \
  --tasks   ~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
  --gen-log ~/e8-run/A1V2-filter/filter-gen.jsonl \
  --out-dir ~/e8-run/A1V2-filter \
  --template ~/e8-run/template.txt \
  --arm-b-instruction ~/repos/closure/experiments/E5-reclosure/ARM-B-INSTRUCTION.md \
  --n-draws 3 --rate 2.0 \
  > ~/e8-run/A1V2-filter/gen.log 2>&1 &
unset ANTHROPIC_API_KEY
# Resumable: banked (task_id, filter_state, draw_index) rows are skipped on re-run.
# This ALSO produces a CPU-scored filter-report.json + pruned-items.json; the GPU re-score below
# supersedes those numbers for certification.
```

Filter SCORING (GPU/MPS, zero spend — model-free NLI; supersedes the inline CPU score):
```bash
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
GEN_LOG=~/e8-run/A1V2-filter/filter-gen.jsonl \
DEVICE=mps THREADS=2 \
bash ~/e8-driver/run_axis_gpu.sh
```

Produces `~/e8-run/A1V2-filter/{filter-report.json, pruned-items.json}`. Precondition: `gpu_probe`
device gate must have PASSED for this corpus/model (Step Zero), same as the registered run.

---

## 2. STAGE-2 — registered-run generation + scoring (447 draws → $3.12)

DRY PLAN (no key, no spend):
```bash
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
E8_RUN=~/e8-run \
bash ~/e8-driver/stage2_generate.sh
# prints: "To actually generate (SPENDS ~$3.12 for this axis), re-run with --go ..."
```

REAL (owner only, spends ~$3.12):
```bash
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
E8_RUN=~/e8-run \
bash ~/e8-driver/stage2_generate.sh --go
```

STAGE-2 SCORING (GPU/MPS, zero spend):
```bash
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
GEN_LOG=~/e8-run/A1V2-stage2/stage2-gen.jsonl \
PRUNED=~/e8-run/A1V2-filter/pruned-items.json \
DEVICE=mps THREADS=2 \
bash ~/e8-driver/run_stage2_gpu.sh
```

Produces `~/e8-run/A1V2-stage2/{batched-stage2-scores.json, results/*.json}` + the equiv gate +
Option-C oracle, exactly like the registered A1 run.

---

## TOTAL X4 GENERATION SPEND: $6.24 (filter) + $3.12 (stage-2) = **$9.36** (matches ≈$9.5 estimate).

Scoring is model-free (NLI on GPU) — zero API spend.

---

## COST-SAVING ALTERNATIVE (owner decision ⚑) — reuse the existing A1 generation, RE-SCORE only

**The transform changed ONLY scoring-side fields.** `sources`, `question`, and `not_A_evidence` are
byte-identical to the original A1 corpus (verified: 447/447). The prompt the generator builds
(`axis_prompt.documents_for_state`) reads only those fields — so the model would receive the SAME
prompt and produce the SAME class of output. The existing registered A1 generation already covers all
447 v2 task_ids (verified: 447/447 present in `A1-stage2/stage2-gen.jsonl`).

Therefore X4 can be scored for **$0** by re-running ONLY the scorer against the existing generation with
the v2 corpus supplying the new (stale-polarity) `must_change`:

```bash
# reuse existing gen; score against v2 must_change
AXIS=A1V2 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A1-depth-v2.jsonl \
GEN_LOG=~/e8-run/A1-stage2/stage2-gen.jsonl \            # <-- the ORIGINAL A1 gen, reused
PRUNED=/dev/null \                                       # or the original A1 pruned set (see caveat)
DEVICE=mps THREADS=2 \
bash ~/e8-driver/run_stage2_gpu.sh
```

CAVEATS the owner must weigh (⚑):
1. **Registration cleanliness.** The registered run pinned specific sampled outputs. Reusing them to
   score a *different corpus* is a re-scoring, not a re-run — defensible because the prompt is identical,
   but it is NOT an independent generation. If X4 is meant to be a fresh, independently-registered
   depth-axis run, regenerate (§1–§2). If X4 is only to CHECK whether the polarity fix changes the
   contamination reading, reuse is sound and free.
2. **Filter pruning.** The original A1 filter pruned against the original (corrected-polarity)
   must_change. The v2 pruning criterion ("stale asserted in correction draws") differs, so the pruned
   set should be recomputed from a v2 filter pass (§1) if pruning is load-bearing for the final table.
   For a first-look re-score, `PRUNED=/dev/null` scores all items.
3. **Sampling nondeterminism.** Reuse gives the exact same outputs the registered run saw; regeneration
   would draw fresh samples (temperature). For a stable A/B against the registered A1 numbers, reuse is
   actually PREFERABLE (same outputs, only the scoring polarity changes) — it isolates the polarity fix.

RECOMMENDATION: for the scientific question X4 exists to answer ("does the depth axis show a real
dose-response once polarity is fixed?"), **reuse the existing generation and re-score** (§ alternative)
as the first, free pass — it isolates the polarity variable perfectly. Regenerate (§1–§2, $9.36) only if
an independently-registered fresh run is required for the record. Owner picks.
