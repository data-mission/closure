# ⚡ COLD-START CHECKLIST — start here (each step verifiable)

1. Machine: ssh -i ~/.ssh/id_rsa vladryzhkov@100.94.88.37 (Mac Mini M4/16GB). Read THIS file fully,
   then ~/e8-run/ops-journal.md (lessons) and ~/e8-run/INTERVENTIONS.log (stop history).
2. Verify banked datasets (nothing to regenerate for the filter tier):
   wc -l ~/e8-run/{A1,A2,A3}-filter/filter-gen.jsonl   → expect 900 / 780 / 672 (paid, $16.42)
   Frozen source corpora (committed): experiments/E8-instruction-breakpoint/corpus-candidates/*.jsonl
   → 450/390/336 rows. Prompt template: ~/e8-run/template.txt (621 B). API key: ~/.anthropic_key (600).
3. STEP ZERO — prove scoring is genuinely on-GPU (never skip): run a test batch via
   ~/e8-driver/gpu_probe.py while watching ioreg GPU utilization >0 and per-op fallback
   (see §6 caveat). If mostly CPU-fallback, fix ops before anything else.
4. CERTIFY (~5 min, quiet box): gpu_probe --cpu-mode near-only vs ~/e8-run/_smoke/serial_gt.json
   + MPS self-consistency (score twice, demand identical). Deliverable: flip count near 0.7.
5. RE-ANCHOR E5 on the certified MPS instrument (60 tasks, minutes) — preserves the E5↔E8 chain.
6. BUILD the batched MPS scorer for minutes-scale (§3c) — new file, equivalence-gated vs
   per-call MPS before use (same discipline as filter_parallel, sha b4346d14).
7. OWNER DECIDES registration treatment (§4: resume / amend / re-register) — then run.
8. Operate per the /mission-ops standard: pre-flight, INTERVENTIONS.log, timestamped logs,
   dashboard, ETAs from measured rates only.

# E8 restart — GPU rewire notes (working notes, uncommitted)

Owner decision 2026-07-18: the E8 run was stopped mid-filter-scoring; the restart will run the scoring
instrument on GPU (MPS), engineered so a full run takes minutes-scale on this machine, not hours.
These notes capture everything measured in the stopped run needed to execute that restart. Nothing here
is committed or registered; the owner decides registration treatment (§4).

## 1. Measured facts from the stopped run (2026-07-17/18)

- CPU frozen path throughput: ~18 s per _still_asserts call at full box occupancy (measured passively
  from timestamped worker logs). Filter tier alone = 8,184 calls (A3 2,244 / A2 2,340 / A1 3,600)
  ≈ 40+ CPU-hours. Not viable on this hardware. Root cause of the slow choice: the apparatus was
  designed without an inventory of available hardware; the GPU was never considered.
- MPS availability: torch 2.13.0, mps available and built. The frozen NLIScorer runs on MPS
  UNMODIFIED via dataclasses.replace(CONFIG.nli, device="mps") — no frozen file edits needed.
- KEY: torch.use_deterministic_algorithms(True) engages on MPS in this build WITHOUT warn_only
  fallback. The assumed determinism blocker does not exist here.
- Measured MPS speed (single stream, unbatched): 4 families scored twice in ~90 s (~11 s/family)
  vs ~17 min/family CPU-under-contention. Uncontended expectation 10–30× CPU.
- Memory: MPS instance drove compressor +1.16 GB/5 min while co-running with 5 CPU model instances
  on 16 GB unified. Rule: GPU scoring runs ALONE, never alongside a CPU scorer fleet.
- INCOMPLETE: flip-rate certification (CPU-vs-MPS boolean diffs near the 0.7 assert threshold) was
  not finished. The probe exists and is redesigned to need ~5 min on a quiet box (§3a).

## 2. Banked assets — the restart does NOT start from zero

- ALL 2,352 filter-stage generations are banked in ~/e8-run/{A1,A2,A3}-filter/filter-gen.jsonl
  ($16.42 already paid; generation never re-runs). Scoring restarts from these logs at no API cost.
- Stage-2 generations (1,176 draws ≈ $8.21) not yet made.
- Tools on disk (~/e8-driver/): filter_parallel.py (sha b4346d14, process-parallel + live metrics),
  gpu_probe.py (sha 33a3647f + staged --cpu-mode near-only variant), oracle_verify_progress.py
  (sha 622924a8, instrumented oracle), filter_stage_progress.py (instrumented serial copy).
  Registered originals byte-untouched throughout (shas recorded in run logs).
- Partial CPU scoring ground truth for certification: ~/e8-run/_smoke/serial_gt.json (4 families)
  plus per-worker completions recorded in paracheck/filter logs.
- Ops apparatus proven and reusable: INTERVENTIONS.log protocol, timestamped log mirrors,
  launch.sh PATH fix (PATH="$HOME/.local/bin:$PATH"), dashboard scaffold, verdict-prep drafts in
  ~/e8-run/verdict-prep/ (skeleton + computation plan, two aggregation traps documented:
  _oracle_result.json exclusion; must_persist never pruned).

## 3. Work plan to "minutes on GPU"

a. CERTIFY (first, ~5 min quiet box): run gpu_probe --cpu-mode near-only — MPS-scores all banked A3
   outputs, CPU-scores only near-threshold items, diffs booleans vs existing ground truth; plus
   MPS run-to-run self-consistency (score twice, require identical). Deliverable: flip count, delta
   distribution near 0.7, self-consistency verdict. Zero flips + self-consistent → GPU instrument
   certified for this corpus/model.
b. RE-ANCHOR the baseline (cheap, critical for the E5 chain): re-score the E5 corpus (60 tasks) on
   the certified MPS instrument — minutes of compute — producing an E5-GPU baseline so E8-GPU
   results remain comparable to the baseline experiment on the SAME instrument.
c. BATCH for minutes-scale: single-stream MPS is ~11 s/family (≈20 min/axis — already acceptable);
   to reach true minutes, batch across calls: collect all (premise, hypothesis) pairs per axis into
   canonically-ordered large batches (fixed composition = reproducible; respect the documented
   batch-composition reproducibility constraint in the harness), tokenize pipelined, fp16 native.
   Realistic batched MPS for DeBERTa-large: 20–60 pairs/s → full filter tier (~53k pairs) in
   ~15–45 min total, per-axis in minutes. Stage-2 scoring same treatment.
d. GENERATION floor: API generation is network-bound (~25 min per full filter tier at rate 2.0
   with 2 threads). Already banked for the filter tier; for Stage-2, raise --rate/threads to the
   provider ceiling to keep total wall dominated by nothing.
e. RUN SOLO: GPU scoring runs with no concurrent CPU scorer fleet (memory rule, §1).

## 4. Registration treatment — owner decides, consequences stated once

(i) Resume the current registration on the frozen CPU path: valid as registered; slow.
(ii) Amend: certified-GPU scoring with full disclosure (certification report attached, config
    re-hashed with device=mps + torch/transformers/OS pins): fast; requires disclosure section and
    accepts amendment critique.
(iii) Fresh registration (E8-r2) naming the certified GPU instrument, with the §3b re-anchored
    E5-GPU baseline: cleanest science on the new instrument; costs a new freeze cycle.

## 5. Decision record

The CPU instrument choice is recorded as a design error: it implemented "frozen instrument" as
"slow instrument" without measuring cost or inventorying available hardware. The requirement was
frozenness, not CPU. Rule for all future apparatus: inventory the actually-available hardware first;
certify the fastest instrument that meets the reproducibility requirement; freeze that.

## 6. Late addendum — fallback caveat (must be step ZERO of certification)

The stopped probe showed 183% CPU while nominally on MPS, consistent with torch silently executing
unsupported ops on CPU per-op (fallback). Before interpreting ANY certification data, first verify
the path is genuinely on-GPU: run with fallback disabled / audit op support, and confirm GPU
utilization during scoring. Certifying a silent CPU-fallback path would be meaningless. The ~11 s/family
speed measurement suggests substantial real GPU execution, but the on-GPU verification was not
completed before the stop.

## 7. Axis-count confirmation: the 8→3 narrowing is COMPUTE-INDEPENDENT (verified against PHASE0 §2)

Owner question: were candidate axes dropped because the CPU instrument was slow? Answer: NO — every
recorded disposition cites a scientific reason; none cite compute cost/speed. GPU speed does not
resurrect any of them:

| Dropped candidate | Recorded reason (PHASE0 §2) | Cured by GPU? |
|---|---|---|
| Context length / distractor volume | per-segment scoring extension is unsound-when-reached and never engages at corpus scale (instrument validity) | NO — validity, not speed |
| Correction-of-correction interleaving | contains correction-count as substrate; a monotone break would be unattributable without matched controls (confound) | NO — attribution logic |
| Assumption-to-correction distance | dose realized as inserted length = instrument collision + length-cluster confound | NO — confound |
| Domain shift of the correction | no naturally ordered ≥3-level dose; thinnest motivation | NO — no dose structure exists |
| Compaction cycles | E8 is registered operator-free; a summarize-and-continue cycle is an operator — staged as its own study (strongest evidence base of all eight) | NO — scope rule; remains the top candidate for its OWN experiment (E9), where GPU speed WILL help |
| Scoped-exception, behavioral/agentic form | not scorable by the frozen NLI instrument (capability, not speed) | NO — needs a different instrument class |

Retained: A1 depth, A2 scoped-exception (propositional), A3 corrections — all three pass the four
selection criteria on scientific grounds. CONCLUSION: the GPU restart keeps 3 axes. The place GPU
speed changes future design space is corpus SIZE / dose RANGE / replication count per axis, and the
compaction-cycles standalone study — not the axis set.
