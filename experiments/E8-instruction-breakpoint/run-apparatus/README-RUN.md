# E8 corpus driver — run guide (Mac Mini M4)

This is the parallel scoring + generation driver for the E8 registered run. It is **built, not
run** — no API calls happen until you launch it with your key, post-freeze. Everything scoring-side
is the **frozen path invoked verbatim** (`outcomes.score` over `NLIScorer`), so a parallel run
produces the identical numbers a serial run would.

## What's in here

| File | Role |
|---|---|
| `common.py` | atomic writes, task-file locking, provenance stamping, pruning loader |
| `score_worker.py` | one scoring worker: claims whole tasks (file-lock), scores via the frozen path, writes one atomic result file per task |
| `calibrate_and_run.py` | orchestrator: 10-min **calibration** → worker **autotune** → parallel run to completion (thermal guard) |
| `oracle_verify.py` | per-task `==` oracle in a **fresh, 1-thread** process; fails loud on any mismatch |
| `generation_driver.py` | concurrent, rate-limit-bound Arm-B generation; reads the key from env; `--dry-run` fake mode |
| `launch.sh` | one-command launcher: caffeinate + nohup, generation → calibrate+score → oracle |
| `dry_run.py` | end-to-end plumbing check at **zero spend** (7 checks incl. filter mode) |
| `axis_prompt.py` | per-axis correction/assumption-state prompt construction (withhold rules) |
| `filter_stage.py` | A-dependency filter: 2 states × 3 draws/family → pruning register + report |

## Before you launch (one time)

1. Harness ready: `cd ~/repos/closure/harness && uv sync` and confirm the pinned DeBERTa model is
   in the local HF cache (the scorer loads offline).
2. Set your key for generation only (never passed on the CLI, never logged):
   ```
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
3. (Optional) defer OS auto-updates so a restart can't interrupt a long run:
   ```
   sudo softwareupdate --schedule off      # ...run... then: sudo softwareupdate --schedule on
   ```

## Verify the plumbing first (no key, no spend)

```
cd ~/repos/closure/harness
uv run python <this-dir>/dry_run.py
```
Prints a 6-check ledger (generation, scoring, oracle, determinism, atomicity, provenance) and
`DRY-RUN PASS` if the whole pipeline is sound. Run this after any change before spending money.

## Launch one axis (the real run)

```
AXIS_DIR=~/e8/axis-depth \
TASKS=~/e8/corpora/depth/tasks.jsonl \
TEMPLATE=~/e8/prompt_template.txt \
ARMB=~/repos/closure/experiments/E5-reclosure/ARM-B-INSTRUCTION.md \
CONFIG_HASH=<the frozen E8 token> \
bash <this-dir>/launch.sh
```

It runs, in order, and streams to `$AXIS_DIR/run.log`:
1. **Generation** — one Arm-B draw per probe task, concurrent, rate-limited, resumable.
2. **Calibration (10 min)** — one worker on a stratified sample; prints the **measured** tasks/s
   and the **real** estimated wall time for the full corpus. No throughput is promised — every
   number is measured on your Mini, on this corpus.
3. **Autotune** — measures 1 vs 2 (vs 3) workers; keeps a 3rd only if it actually gains ≥1.5×;
   prints the chosen worker count.
4. **Scoring** — runs to completion with a thermal guard (drops a worker if sustained throughput
   decays >20% over 30 min). Resumable: re-run `launch.sh` and it skips finished tasks.
5. **Oracle** — re-scores a per-worker-stratified sample in a fresh 1-thread process, compares
   **per-task** `==`. Prints `PASS`/`FAIL`. A `FAIL` names the worker whose tasks diverged — treat
   it as a corrupt-environment signal, not a rounding issue.

## What it prints

- `[gen] N/M (ok=… err=…)` — generation progress.
- `[calibrate] RESULT {…measured_tasks_per_s_1worker, est_wall_h_1worker…}` — your real schedule.
- `[autotune] CHOSEN worker count: K`.
- `[run] progress X/total (rate t/s, Kw)` — scoring progress, with thermal-guard events.
- `[oracle] RESULT {verdict, per_worker_coverage, n_mismatches}` — the acceptance gate.

Final scores are one JSON file per task in `$AXIS_DIR/results/`, each stamped with
`provenance` (thread count, torch/transformers versions, hostname, config hash, frozen-path
marker).

## Monitor / stop / resume

```
tail -f $AXIS_DIR/run.log                 # watch
bash <this-dir>/launch.sh --stop $AXIS_DIR   # stop (kills the process group)
# resume: re-run the same launch command — generation, scoring, and oracle are all resumable
```

## Corpus schema canon (rules the driver + aggregator follow)

- **`dose_level` is an INT** (1/2/3), not a string. The corpus is authoritative; the driver
  carries it through verbatim.
- **`break_side`** (`"must_change"` | `"must_persist"`) selects which item list carries the
  verdict-bearing rate.
- **`verdict_item`** (in `axis_params`) is a boolean list parallel to the `break_side` item list;
  `true` marks a verdict-bearing conclusion, `false` a descriptive stratum. **ABSENT ⇒ all-true
  default** over the `break_side` items (A2's corpus omits the field — every break_side item is
  verdict-bearing). The driver encodes this default explicitly and records
  `verdict_item_defaulted: true` on the result when it applied, so a missing field is a RULE, not
  an accident. All items (verdict + descriptive, both sides) are always scored and reported; only
  the marked subset carries the verdict.
- **Per-level N is the ACTUAL count** of verdict-bearing kept items across the corpus, never a
  nominal 150. The driver hands the aggregator the raw per-item asserted flags to compute it.

- **Frozen ARM-B instruction, appended for EVERY axis, hash-pinned.** The pinned
  `ARM-B-INSTRUCTION.md` (sha256 `f9c24295…`) is appended after the question for A1, A2, AND A3,
  identically — E8 studies the INSTRUCTED baseline, so an un-instructed prompt voids the axis. The
  generation driver asserts the instruction file hashes to the pin at startup (fail-loud; override
  only with `--allow-unpinned-instruction` for local template tests), and the append itself is
  fail-loud (a missing `Provide your answer` marker raises rather than silently dropping the
  instruction).

## Safety properties (why this is trustworthy)

- **Frozen path verbatim.** Workers call `outcomes.score(NLIScorer(), output, annotations)` — the
  exact call `run_arms.py` phase 3 made. No custom composition, no re-batching, no cache/replay.
- **Parallel == serial by construction.** Task-sharding is request-preserving for the base scorer
  (each `score` call's bs=16 batch is a pure function of `(sources, claim)`), so splitting tasks
  across workers cannot change a score. The oracle proves it per-run.
- **Crash-safe.** Result files are written temp+atomic-rename; a task lock is held until after the
  rename; resume skips only complete files. A killed worker loses no committed result and its tasks
  are re-scored cleanly.
- **Measured, not promised.** No throughput claim is baked in; the 10-min calibration prints the
  real schedule for your machine before the full run commits.
- **Provenance on every result.** Thread count and versions are recorded (thread count is not a
  frozen field, so recording it is how a mismatched-environment worker becomes detectable).
- **Zero spend until you launch.** Generation is the only thing that spends, needs your key, and is
  fully resumable; scoring and the oracle need no key.
