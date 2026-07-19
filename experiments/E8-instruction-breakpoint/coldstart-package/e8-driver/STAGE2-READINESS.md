# STAGE-2 READINESS — generation (ready) + scoring (design + one decision for the lead)

Command-authoring + local verification only; nothing run on the Mini. Two parts: (1) Stage-2
GENERATION (owner-gated spend) — authored + verified; (2) Stage-2 SCORING — a structural finding
that means it is NOT just "point run_axis_gpu.sh at the Stage-2 log"; needs a decision.

New file: `stage2_generate.sh` (this dir). No new scoring file yet — see §2 (decision-gated).

================================================================================
## 0. What Stage-2 IS (reconciled from the code)

Stage-2 = the REGISTERED-RUN generation + scoring of the FULL corpus (post-filter), Arm-B only.
- GENERATION: one Arm-B draw per corpus row (NOT the filter tier's 2-state × 3-draw structure).
  `generation_driver.py` does one generation per (task, arm=B), no --n-draws (generation_driver.py:164).
- Row counts (verified: corpus-candidates line counts == the family-fingerprint run.log counts):
  A1 450 + A2 390 + A3 336 = **1,176 draws** — exactly the "1,176 draws ≈ $8.21" in GPU-REWIRE-NOTES §2.
- SCORING: `score_worker.score_one_task` (score_worker.py:53-138) scores each task's Arm-B output
  against BOTH `must_change` AND `must_persist` via the frozen `outcomes.score()` + `_still_asserts`,
  emitting a rich per-task result: `{task_id, kept_change_indices, routing{family_id, axis,
  dose_level, break_side, verdict_item, verdict_item_defaulted, item_roles},
  arms{B{n_items, contaminated_items, contamination, completeness,
  must_change_asserted_by_index, must_persist_asserted}}}`. One JSON per task in
  `~/e8-run/<axis>-stage2/results/` (or wherever --out-dir points).

================================================================================
## 1. STAGE-2 GENERATION — `stage2_generate.sh` (READY, owner-gated)

Per axis: `generation_driver.py --arms B` over the raw corpus-candidate file, resumable, ARM-B
hash-pinned, rate raised toward the provider ceiling (GPU-REWIRE-NOTES §3d).

### Key handling (owner-gated spend, key never leaks)
- Requires an explicit `--go` flag AND `~/.anthropic_key` present. Without `--go` it prints the plan
  + per-axis cost and spends nothing (dry).
- Reads `~/.anthropic_key` into `ANTHROPIC_API_KEY` at launch, exports it, never echoes/logs/CLIs it.
  `set +x` forced in both parent and detached child so no trace can leak the value. The frozen
  provider reads `ANTHROPIC_API_KEY` from env per call and never prints it (providers.py:106). Grep
  confirmed: the key var appears in NO echo/tee/log line.
- Refuses a non-600 key file (defensive) and an empty key file.
- ARM-B pin: passes `experiments/E5-reclosure/ARM-B-INSTRUCTION.md`
  (sha256 f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c — VERIFIED matches the
  generation_driver.py:144 pin); does NOT pass --allow-unpinned-instruction. Driver refuses any
  other instruction at startup.

### Inputs — provenance verified, Mini reachability
- tasks (per axis): `~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/<axis>.jsonl`
  (committed at HEAD, on the Mini via git).
- template: `~/e8-run/template.txt` (621 B, has {documents}/{question}/"Provide your answer"; the
  Mini's working copy from the original run — NOT committed, but the run apparatus is already staged
  on the Mini per the lead's 15:45Z note; confirm it's present before --go).
- ARM-B: `~/repos/closure/experiments/E5-reclosure/ARM-B-INSTRUCTION.md` (committed at HEAD ✓).

### EXACT Mini commands (owner runs)
Dry plan (no key, no spend):
```
AXIS=A3 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
bash ~/e8-driver/stage2_generate.sh
```
Real generation (SPENDS — owner only, ~$8.21 total across axes; per-axis A1 $3.14 / A2 $2.72 / A3 $2.35):
```
AXIS=A3 \
TASKS=~/repos/closure/experiments/E8-instruction-breakpoint/corpus-candidates/A3-corrections.jsonl \
bash ~/e8-driver/stage2_generate.sh --go
# tail: tail -f ~/e8-run/A3-stage2/stage2-gen.log   stop: bash ~/e8-driver/stage2_generate.sh --stop A3
```
(Repeat for A2 / A1 with their corpus-candidate paths.) Output log: `~/e8-run/<AXIS>-stage2/stage2-gen.jsonl`.
Generation is network-bound and independent of the GPU, so it can run WHILE the GPU scores the
filter tier (it is not a model process) — but it SPENDS, so it waits for the owner regardless.
Raise `RATE=` / `CONCURRENCY=` env toward the provider ceiling if tolerated (defaults 4.0/s, 8).

### Verified locally
bash 3.2 parse OK; no bash-4 features; dry plan prints correct draw count + cost ($2.35 for A3's
336 rows == 336/1176×8.21); `--go` without a key file REFUSES (exit 3) and spends nothing; key var
never in any output line; exports (incl. ANTHROPIC_API_KEY) reach the detached child.

================================================================================
## 2. STAGE-2 SCORING — STRUCTURAL FINDING + DECISION NEEDED (no file authored yet)

### The finding: Stage-2 scoring is a DIFFERENT shape than filter scoring
`batched_scorer.py` (the filter batched path) collects `must_change` pairs from the filter-gen
structure (fam, state, draw, item) and emits per-(fam,state,draw,item) raw+bool. Stage-2 scoring
(`score_worker.score_one_task`) is different:
- scores per TASK (full corpus, all dose levels), Arm-B only;
- scores BOTH `must_change` AND `must_persist` via frozen `outcomes.score()`;
- emits contamination + completeness + per-item asserted flags + routing metadata (verdict_item,
  dose_level, break_side, item_roles) — the exact shape the verdict compute-plan consumes.

So `run_axis_gpu.sh` / `batched_scorer.py` CANNOT score Stage-2: pointing them at the Stage-2 log
would produce the filter result shape (must_change-only, no routing), not the registered-run result
files the verdict aggregation reads. Confirmed against verdict_compute-plan.md §1 (it reads
`results/<task>.json` in score_worker's shape) and score_worker.py:53-138.

### Same frozen-composition constraint applies
score_worker.py:5-14 states the H1 invariant explicitly: parallelism is ACROSS whole tasks, each
`outcomes.score` call is a self-contained bs=16 batch, "NO custom composition, NO re-batching". A
cross-task BATCHED Stage-2 scorer would re-batch across tasks — the SAME composition change the
filter batched path makes — so it would need the SAME equivalence gate (batched vs per-call
zero-flip) before use. It is not automatically safe.

### DECISION: PATH B CONFIRMED by lead (2026-07-18) — batched Stage-2 GPU scorer, AUTHORED.
(A was: score on the existing CPU path — rejected, it's the slow instrument the rewire exists to
avoid, 1,176 tasks × ~18 s.) Path B is built + logic-verified below.

Files authored (this dir):
- `batched_stage2_scorer.py` — mirrors `score_worker.score_one_task` (score_worker.py:53-138): both
  annotation sides (must_change post-prune + must_persist), per-item flags keyed by original index,
  contamination/completeness fractions, `contaminated_items` rounding, and the full routing block
  (verdict_item all-true default, break_side, dose_level, item_roles). Reuses batched_scorer's
  `build_scorer` (MPS monkeypatch) + `score_pairs_batched` (canonical fixed-composition forward).
  Keys gen selection on the BANKED CPU hash (auto-detected from the gen log's first row), --device
  moves only the scorer (reanchor_e5_mps pattern; lead-confirmed gens carry 6dbe47a8). Optionally
  writes one score_worker-shaped JSON per task into `--results-dir` (the verdict compute-plan's
  input layout) plus an aggregate JSON.
  OPTIMIZATION (provably safe): score_one_task scores each conclusion twice (inside frozen score()
  for the fraction, then again for the per-item flag) — both are the SAME pure scalar(premises,concl)
  call, so the batched path scores each unique (task,arm,side,item) conclusion ONCE and derives both.
- `batched_stage2_equiv.py` — batched-vs-per-call gate. Per-call reference = score_worker.score_one_task
  invoked verbatim; ONE shared scorer both paths. Diffs every per-item change flag + persist flag +
  the derived contamination/completeness fractions; PASS iff zero flips AND zero fraction mismatches
  AND no task/arm key-set mismatch; exits nonzero + loud FAIL otherwise. `--n-tasks` for a cheap shard.
- `run_stage2_gpu.sh` — per-axis GPU-solo driver: full equiv gate (EXIT-CHECKED → ABORT on flip) →
  scored pass. Same trap set as run_axis_gpu.sh (PATH prefix, HF offline, INTERVENTIONS entries,
  timestamped tee, caffeinate/nohup/pid/--stop, exported vars for the detached child, pre-flight
  existence checks). GPU-SOLO: sequence after the filter tier / E5 / other axes.

VERIFIED (as far as possible without the model — the model-level padding equivalence is the equiv
gate's job on real gens): all 3 files syntax-clean; run_stage2_gpu.sh parses under bash 3.2.57, no
bash-4 features; all four modules import cleanly together (no circular imports). LOGIC PROOF: with a
shared FAKE deterministic scalar injected into BOTH score_one_task and the batched pipeline, the
batched reassembly reproduces IDENTICAL per-item change bools, persist bools, contamination/
completeness (to 1e-12), contaminated_items rounding, kept_change_indices, and routing (verdict_item)
across pruning (dropped index → kept subset), explicit verdict_item, and a must_persist break_side —
zero flips, zero fraction mismatches. This proves the composition/reassembly/result-shape code I
wrote; the equiv gate proves the model-level padding-composition equivalence on real gens.

### Also flag: same CPU-vs-MPS config_hash issue will apply to Stage-2 scoring
`score_worker` keys gens by the live `config_hash` (score_worker.py:174). If Stage-2 gens are
generated on the Mini under the CPU config and then scored on MPS, the live MPS hash won't match —
the same zero-select trap I found for E5. A batched Stage-2 scorer must handle this the way
reanchor_e5_mps.py does (key selection on the gen's banked hash, device only on the scorer). Worth
deciding whether Stage-2 gens are stamped with the CPU or MPS hash at generation time.

================================================================================
## 3. Summary for the lead
- Stage-2 GENERATION: `stage2_generate.sh` ready + verified; owner-gated, key-safe, hash-pinned,
  provenance-verified inputs; exact commands above. Waits on the owner's spend decision.
- Stage-2 SCORING: needs a decision (A CPU vs B batched-GPU; I recommend B) and real Stage-2 gens
  before the batched scorer + gate can be authored and run. Flagged the config_hash trap too.
