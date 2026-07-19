# MISSION X — VERDICT (stream-closure document)

STATUS: FINAL (2026-07-19) — all three runs landed: X4 depth NO-BREAK (true floor 0/447), X6 pilot
VOID (corpus defect, harness correctly withheld), E9 compaction HOLDS CLEAN (0/1800 real). Every section
is settled; the two ⚑ owner acts that remain are the E5 correction-note publication and the X-HUMAN
annotation, both outside this document. Conventions follow the repo's VERDICT-skeleton.md.

Base: closure@689833c + uncommitted mission-x. Adjudication of record: `SYNTHESIS-GATE.md`.
Owner: everything authorized, no ceiling, per-launch disclosure, exploratory grade. ⚑ = owner decision.

---

## 0. Headline (FINAL)

Mission X was a post-verdict adversarial audit of the E8 instruction-breakpoint program. Its
convergent finding: **the measuring instrument — not the model — was the modal failure class of the
entire revision line.** Every "revision failure" the program had measured re-adjudicated to an NLI
template-collision artifact. Under a claim-grounded instrument, instructed revision is ROBUST on every
validly-measured corpus, and **the operator line has NO measured opening in ANY regime tested —
single-shot (E5), depth (X4), or compaction (E9).** Instrument↔corpus coupling errors were found and
disclosed by the program's own audit, pre-external-discovery: A2 wrong-side counting, A1 polarity
inversion, A3 template collision, E5 Arm-C separation, and the E9 frozen-NLI rising-S-curve — five
independent appearances of the same template-collision artifact, each of which would have produced a
false positive under the pre-audit instrument. X6's pilot was VOID for a distinct reason (a corpus-
construction defect, correctly caught by a withholding harness — the model's refusal to fabricate was
the good behavior).

The E8 program verdict (Block B, no axis broke) STANDS and is unaffected. E5's registered refutation
of the release-time operator hypothesis (H-RELEASE) is WITHDRAWN and REOPENED. Mission X workload
(measurement provenance, §5): E9 900/900 finals across 150 F3 families × 2 arms; X6 pilot 280 specs
/ ~1,920 turns (VOID — corpus defect); X4 re-scored on banked generations (no new draws).

---

## 1. The instrument findings — chronology (FINAL)

Five appearances of the SAME NLI template-collision artifact (#1-4, 6), one distinct real defect (#5),
and one corpus-construction defect (#7). Every "revision failure" the program measured is here.

| # | finding | corpus | mechanism | re-adjudicated result | evidence |
|---|---|---|---|---|---|
| 1 | A2 wrong-side counting | E8-A2 | scorer counted retention, not the drop (must_persist break side) | fixed → 13/12/14 of 260, crossed=FALSE; program verdict unchanged | verdict-numbers.pre-a2fix.json + PHASE0 §3 |
| 2 | A1 polarity inversion | E8-A1 | must_change held the CORRECTED value → axis measured revision SUCCESS, not contamination | 450/450 confirmed; rebuilt + rescored by X4 (§2.4): NO BREAK, depth robust — depth question settled | X1/P2/red-check + X4 |
| 3 | A3 template collision | E8-A3 | shared "{number}{verdict}{threshold}" scaffold clears NLI 0.7 | 200 flags → 0 real; full sweep 0/786 (machine-provable after unit guard) | X1-FINDINGS + instrument_v2 |
| 4 | E5 Arm-C separation | E5 | contraction retains superseded claims → more scaffold premises → higher raw flag count | 0/11 real echo; B-arm 0/1 same item both arms; B-vs-C separation is artifact | E5-ARMC-REEXAM.md |
| 5 | DANGLING_RULE (distinct, real) | E5 Arm-C | contraction computes corrected value + retains rule but never draws the Boolean | 2/11 — a real completeness defect, NOT contamination; fix specced | DANGLING-RULE-FIX-SPEC.md |
| 6 | E9 frozen-NLI rising S-curve | E9 (compaction) | supersession-scaffold collision produced a 0/9/18 rising curve — the exact shape that would falsely confirm H-COMPACT | 0/27 real (all 900 stale-total pairs screened); v2 0/1800 real | §2.7 + panel-necessity screen |
| 7 | X6 corpus-construction defect (distinct) | X6 pilot | x6_build gave rule+exception but not per-case FACTS → model can't compute → refuses | pilot VOID; harness correctly WITHHELD; model's refusal was the GOOD behavior; ⚑ re-run | §2.6 + FF-TAXONOMY.md |

Common root: bidirectional DeBERTa-v3-large-MNLI at 0.7, max-over-premises, fires on shared
requirement scaffolding between stale and corrected sentences. The replacement (instrument-v2) scores
claim-grounded value/verdict echo and certified 4/4 gates + adversarial positive controls (it can fire).

---

## 2. Per-axis / per-experiment verdicts

### 2.1 E8 program verdict (FINAL)
**Block B — no axis broke** under the registered conjunctive definition (monotone rise across ≥3
levels AND θ-crossing at the top, surviving multiplicity). axes_broke = []. Independent of the A1
polarity finding (Block B rests on A3 correctly-polarized + A2 fixed). Instrument certification: all
gates green, zero flips; oracles PASS 0/12 each; workload = 3,528 banked draws (filter 2,352 +
Stage-2 1,176), 0 error rows, §5. (E8 canonical numbers: `~/e8-run/verdict-prep/verdict-numbers.json`.)

### 2.2 A3 corrections (FINAL)
Registered θ=5% flag rate 26.7/29.4/24.1% (flat, non-monotone → no break). **Real contamination = 0**
across the full 786-item must_change sweep (verdict basis 756 post-pruning) under instrument-v2. The
floor was NLI template collision; the model integrated every correction.

### 2.3 A2 scoped-exception (FINAL)
must_persist break side, θ=10%. Drops 5.0/4.6/5.4% (below θ, flat) → clean no-break. (Corrected from
the wrong-side retention count.)

### 2.4 A1 depth — INVALID AS BUILT (registered) → REBUILT + SCORED by X4 (FINAL)
The REGISTERED A1 measured revision SUCCESS (polarity inversion), not contamination — contributed no
depth-failure evidence. Registered per-dose revision success (the honest per-dose truth): 52% / 97% /
94% at D1/D2/D3 — the D1 52% a dose-1 insurance-vs-primary item-role composition artifact, not a depth
effect, and exactly why X4 was needed. X4 rebuilt the corpus (stale-world must_change + insurance drop;
polarity verified correct at build — check_v2.py: 0 corrected-world leaks across 447 records) and
re-scored it on the certified instrument. **X4 verdict FINAL:**

| dose | count | trials | rate |
|---|---|---|---|
| D1 | 0 | 149 | 0.000 |
| D2 | 10 | 149 | 0.067 |
| D3 | 3 | 142 | 0.021 |

- Cochran-Armitage trend Z = 1.110, one-sided p = 0.133 → ca_uptrend = TRUE.
- Strict observed rise (p̂ D1<D2<D3): FALSE (D3 0.021 < D2 0.067); gate_pass = FALSE (needs both conjuncts).
- Top-level crossing vs θ=5% at α_corr: k* = 14, observed 3, p = 0.975, crossed = FALSE (p̂=0.0211 < θ=0.05).
- **A1 BREAK: FALSE** (all three conjuncts required; gate fails on strict_rise, crossing fails at top).
  Interpretation: **DEPTH QUESTION SETTLED — no depth-breakpoint; instructed revision is ROBUST across
  derivation depth on the correctly-polarized axis.** The two-sided pre-stated conclusion branch "clean
  null → depth settled" fires (SYNTHESIS-GATE §4).
- VALIDITY (A1V2): polarity verified correct at corpus build (check_v2.py, 0 corrected-world leaks,
  447 records). [The validity_note field in the X4 verdict-numbers.json is the STALE hardcoded old-A1
  polarity text and does NOT apply to the v2 run — not carried here.]
- TRUE FLOOR (instrument-v2 screen COMPLETE): panel-necessity's claim-grounded screen adjudicated ALL
  13 NLI-flagged items as artifacts (11 FP_TEMPLATE, 1 FP_SUPERSESSION, 1 label-collision; per-item table
  in its report to main). So the raw NLI-flagged rate 13/447 = 2.9% is the instrument-basis number, but
  the **TRUE depth floor is 0/447 = 0.0% real contamination at any depth** — the NO-BREAK verdict holds
  and is now a real-zero, not merely a not-crossed. Same template-collision class as A3/E5.
  TOOLING NOTE: the canonical instrument_v2 needs an A1-corpus adapter (correct-final read from derivation
  NODES, not state_values) before any AT-SCALE A1 screen — these 13 were HAND-certified; tool-certification
  for A1 is future work.
- Validity: oracle PASS 0/12 mismatches (447/447 records present). Disclosures: 149 families, 141
  passed, 8 excluded, 25 pruned. Chain: Tier-1 equiv 0 flips → 47,202 pairs scored → converter →
  Stage-2 shard-equiv 0 flips → 28,072 pairs scored → fresh-CPU oracle PASS.
- X4 workload: reuse path — no new generation; the registered A1 generation already covers all 447
  task_ids, so X4 re-scored those banked draws on the certified instrument. Fresh-gen (894 filter + 447
  Stage-2 draws) was PREPARED (PREPARED-GENERATION-COMMANDS.md) but NOT exercised.

### 2.5 E5 reclosure — H-RELEASE REOPENED (FINAL)
Registered B-vs-C contamination separation (Arm-B 0.9% vs Arm-C 10.3%) was read as evidence that the
contraction operator injects contamination instructed revision avoids — refuting H-RELEASE. Re-exam:
**0/11 Arm-C real echo; 0/1 Arm-B real echo; the SAME item (F1-0016/1) flags in BOTH arms** —
airtight proof the flag tracks sentence template, not behavior. All three E5 arms ≈0 real; C's higher
raw count is contraction OUTPUT SHAPE (retains superseded claims as contrasts), not contamination.
The registered separation does not exist under a valid instrument. **H-RELEASE: REFUTED → REOPENED.**
Correction note drafted (CORRECTION-NOTE-DRAFT.md); ⚑ publication = owner. Distinct real defect:
DANGLING_RULE completeness gap (finding #5), fix specced, gated to future retest, does not touch the
frozen path.

### 2.6 X6 behavioral scoped-exception — PILOT VOID for its behavioral purpose (WITHHELD; corpus defect)
Tests whether SCOPED over-generalization (applying a case-scoped exception beyond its scope) rises with
dose AND exceeds the BLANKET decay baseline — the last untested FORM of the original observation.
**X6 verdict: WITHHELD; the pilot is VOID FOR ITS BEHAVIORAL PURPOSE.** Generation completed (280/280),
but the verdict harness's acceptance gate FAILED and the harness respected its exit-2 rule (it refused
to score) — correctly, because the pilot cannot answer the behavioral question at all.

- ROOT CAUSE (red-check real-data capture, lead-verified — OVERTURNS the initial parser-narrowness read;
  updated in _dev_notes/x6-ff-diagnosis/FF-TAXONOMY.md, old hypothesis kept for the record):
  a **corpus-construction defect in x6_build**. The worksheet gives the model the RULE ("2% of insured
  value") and the EXCEPTION but NOT the per-case FACTS (insured values, kWh, hours), so the model CANNOT
  compute rule-case values — there is nothing to compute from. Capture evidence: **30/30 sampled replies
  are missing-input refusals; RULE/NEW cases answered 0/90; EXCEPTED answered 13/15** (their facts ARE in
  the prompt). The extraction-parser issue ("2" grabbed from "2%") is a SECONDARY victim, not the cause;
  x6_normalize is clean.
- THE MODEL'S BEHAVIOR HERE IS THE GOOD BEHAVIOR: it refused to fabricate values it wasn't given and
  asked for the missing inputs. So the run measures a corpus bug, not model drift.
- Acceptance gates (as recorded, now re-attributed to the corpus defect): AC1 PASS (280/280); AC2 FAIL —
  FF-cell rate 0.7368 vs 0.05 tol (tt=0); AC3 blanket decay 0.8333 / 0.85 / 0.8167, dip 0.033 (= 0.69 SE
  at n=60 → noise, a knock-on of the same artifact). verdict_gate = WITHHOLD → X-HUMAN. No θ/δ derived,
  no p_over/p_decay verdict computed (exit-2 respected).
- FF taxonomy (kept for the record; cause re-attributed): 651 total FF (aggregator's 336 = SCOPED-only);
  517 (78%) parser-returned-nothing on prose refusals; 134 (22%) fragment grabs (111 sub-100 like "2"
  from "2%"); ~23 residual for human eyes. These are DOWNSTREAM of the missing-facts refusals.
- RULING: the corpus defect is an ⚑ OWNER-GATED RE-RUN, fix list = (1) embed the per-case facts in the
  worksheet (x6_build transform + re-gen), (2) generation-side typed-output enforcement, (3) bank the raw
  replies (x6_generate did not persist them — a named harness gap). The extraction parser is NOT the
  frozen instrument and may be corrected, but ONLY under X-HUMAN human-label validation — no self-blessed
  re-parse.
- Consequence: X6 does NOT settle the behavioral-form question in this pilot; it surfaced a corpus bug
  and correctly withheld. The behavioral question remains open pending the re-run. The WITHHELD gate is
  the system working. Source: `~/e8-run/x6/x6-acceptance.json` + the capture INTERVENTIONS entries.
- X6 workload (two distinct items): (1) the PILOT GENERATION — launch entry 01:22:10Z "280 specs,
  ~1,920 turns" (280/280 generated); (2) the raw-reply CAPTURE that characterized the corpus defect
  (~220-turn capture; x6_generate didn't persist replies, so the replies were re-captured against raw
  output). Per red-check's INTERVENTIONS log lines.

### 2.7 E9 compaction cycles (H-COMPACT) — HOLDS CLEAN (FINAL): corrections survive compaction
Iterated summarize-and-continue operator vs a matched no-compaction baseline on a correction-fidelity
DV — the operator question's only live opening after E5-C resolved to artifact. **E9 VERDICT:
H-COMPACT HOLDS CLEAN — corrections SURVIVE compaction cycles; the operator does NOT accumulate
revision error at this operating point.**
- v2 contamination = **0 / 1800 real at every (arm, dose)**: N-arm 0/150, 0/300, 0/450; S-arm 0/150,
  0/300, 0/450. No real correction loss under compaction on either arm.
- Frozen-NLI cross-check: the OLD instrument showed a RISING S-curve 0 / 9 / 18 (3.0% / 4.0%) — the exact
  shape that would have FALSELY confirmed H-COMPACT under the pre-audit instrument — but the screen found
  **0/27 real, all supersession-scaffold artifact** (panel-necessity screened ALL 900 stale-total pairs:
  stale absent 900/900, corrected totals asserted; per-item table in its report, appendix incoming). The
  N-arm frozen-NLI is 2/2/2 flat (the same 2 items). This is the SAME template-collision artifact class
  as A3/E5 — E9 is its fifth independent confirmation.
- Comparability gate: 33/1800 = 1.83% ≤ 2% → PASS (the two arms are comparably scored).
- SCOPE LIMITS (verbatim): one model (claude-sonnet-5), one pinned compression band (30–50%), summarizer
  sha 305f7e27 — E9 measures compaction AT that operating point; it does not generalize to other models,
  bands, or summarizers.
- Provenance: corpus manifest 958d77c4 (150 families, guards 150/150), 900/900 finals with 0 errors,
  10-shard parallel generation (disclosed in §6 deviations; zero science change, resume-bank lossless),
  derived MPS scorer sha b0aae68d → 5dbadf43 (3-line device change, diff-verified).
- E9 novelty (final): NON-DUPLICATE on 3 axes vs the compaction papers (§3); does NOT claim primacy on
  iterating compaction (2607.08032 iterates it for end-task error; E9's claim is a matched baseline on a
  correction-fidelity DV).

---

## 3. Novelty / non-duplication verdicts (FINAL — from the owner-ordered sweep, #23)

| artifact | nearest prior art | differentiation (verified) | verdict |
|---|---|---|---|
| instrument-v2 | Proof-Carrying Numbers (arXiv:2509.06902) | shares span-verification substrate + adopts its policy vocab {exact/rounding/alias/tolerance}; NEW = stale↔corrected PAIR reference, directional echo, supersession-exclusion, verdict channel. PCN = faithfulness-to-source; v2 = revision-fidelity | NON-DUPLICATE (substrate shared, task distinct) |
| instrument-v2 extractor | QuanTemp (arXiv:2403.17169) | claim-vs-evidence fact-checking, no supersession/echo; usable only to spot-validate v2's extractor, not its task | NOT A TASK ANALOG (optional extractor validation) |
| X4 depth-as-dose | STALE (arXiv:2605.06527) · TRACK (arXiv:2601.15495) | STALE tests binary 0/1-hop + flags multi-step as open; TRACK doses on fact-COUNT not chain DEPTH. X4 = graded 1/2/3-hop derived-value chains, scored through the derivation graph | NOVEL — lands in STALE's explicitly-flagged-open gap |
| E9 compaction-cycles | rate-distortion compaction (arXiv:2607.08032) · Governance Decay (2606.22528) · Drift No More (2510.07777) | E9 DV = instructed-revision fidelity (not end-task error / constraint erasure / KL drift) + operator-vs-no-compaction matched baseline on a revision task | NON-DUPLICATE on 3 axes; does NOT claim primacy on iterating compaction |
| X6 behavioral scoped-exception | SRD (arXiv:2604.20911) · Constraint Drift (2605.10481) · Governance Decay (2606.22528) · PhantomPolicy (2604.12177) | SRD's constraints are UNCONDITIONED blanket rules (no condition C, no "R except when C"); X6 adds the scoped-exception over the same harness and measures the increment p_over − p_decay over SRD-class blanket decay; registered operator-free + compaction-free | NOVEL — occupies SRD's named gap (scoped-exception form); confirmed by the #23 sweep |

---

## 4. Retirements (FINAL)

- **X3 (operator rematch) — RETIRED AS SCOPED.** No failing regime exists to bite on; every measured
  failure was instrument artifact. The operator question survives only via E5-C re-exam (resolved:
  artifact), X5/E9 (compaction), or a genuine failure on harder corpora later.
- **X2 (bridge) — RETIRED.** No failing regime to bridge; P3+P4 decorative verdicts stand.
- Dropped E8 axes: context→X0 (checkpoint amendment, not per-segment), compaction→X5/E9,
  behavioral→X6; correction-of-correction + distance stay retired (design confounds); domain-shift retired.

---

## 5. Workload & provenance ledger (FINAL)

Measurement provenance only: what ran, how many draws/turns, on what instrument, with what result
integrity. Draw and turn counts are the scientific record; they are counted from the banked generation
jsonls (0 error rows unless noted), not estimated. (Cost figures are deliberately excluded from the
scientific record.)

| item | status | generation workload | scoring instrument | integrity |
|---|---|---|---|---|
| E8 full program (filter + Stage-2 + oracles) | closed | 3,528 banked draws = filter 2,352 (A1 900 + A2 780 + A3 672) + Stage-2 1,176 (A1 450 + A2 390 + A3 336); 0 error rows | frozen NLI (device CPU→MPS, gate A_ZERO_FLIPS 0/84) | oracles PASS 0/12 each; all equiv gates 0 flips |
| Mission X critical path (instrument-v2, A3 rescore, E5-C re-exam) | closed | no new generation (banked E8/E5 draws re-scored) | instrument-v2 (accepted) | A3 786-item surface 0 real; E5-C 0/11 real |
| X4 A1-depth-v2 rebuild + rescore | closed | no new generation — registered A1 gen already covers all 447 task_ids; fresh-gen (894 filter + 447 Stage-2 draws) PREPARED (PREPARED-GENERATION-COMMANDS.md) but NOT exercised | certified instrument (A1-depth-v2) | oracle PASS 0/12; Tier-1 + Stage-2 equiv 0 flips |
| X6 behavioral pilot | closed (VOID — corpus defect) | pilot generation 280/280 (launch 01:22:10Z: "280 specs, ~1,920 turns") + ~220-turn raw-reply capture | acceptance gate WITHHELD (corpus defect — could not score) | 30/30 raw replies = sound missing-input refusals |
| E9 compaction | closed | 900/900 finals across 150 F3 families × 2 arms × doses k=1..3; 0 errors; 10-shard parallel generation | dual scorer: instrument-v2 + frozen-NLI comparability | v2 0/1800 real; frozen-NLI 0/27 real (screened); comparability 1.83% ≤ 2% |

Draw-count basis note: the banked gen records carry NO per-call usage/token fields (keys: arm,
config_hash, draw_index, output, prompt_sha256, reported_model, task_id, ts). Every workload figure
above is a counted draw/turn count from the jsonls, not a token-summed invoice — that is the exact,
verifiable scientific quantity, and no other per-call quantity exists in the record.

---

## 6. Deviations register (FINAL — carried from the E8 §4 disclosure)

1. Scoring device CPU→MPS (config_hash not re-hashed; device gate A_ZERO_FLIPS 0/84; E5 chain_holds).
2. Oracle validity gate substituted (Option C bounded stratified fresh-CPU per-task cross-check).
3. Composition gate shard mode (EQUIV_N_TASKS=30), mid-run throughput decision, layered on twice-proven equivalence.
4. Filter-report reconstruction (byte-gated vs frozen _smoke outputs).
5. Instrument-v2 replaces the registered NLI contamination flag for the AUDIT (not the frozen run) —
   claim-grounded, PCN-vocab, 4/4 gates + adversarial positive controls; frozen artifacts unchanged.

---

## 7. Owner-pending ⚑ decisions (FINAL list)

- ⚑ E5 correction-note PUBLICATION (draft ready: CORRECTION-NOTE-DRAFT.md) — venue, public status
  wording, dangling-rule placement (same note or separate). Publication is the owner's act.
- ⚑ E8 registration treatment — amend (disclosed-GPU) vs re-register (E8-r2 with E5-GPU re-anchor).
- ⚑ X-HUMAN annotators — the NLI human-validation (≥100 items × 2 annotators, κ) is owner-mediated;
  annotator recruitment/scheduling is the owner's.
- ⚑ X0 — build the long-context NLI checkpoint amendment vs reframe the context axis as scoped-out
  (soundness-gated; per-segment pre-rejected).
- ⚑ "All dots of closure" — whether to add E4-enforce / E6 / E7 / E3-registered campaigns.
- ⚑ Non-synthetic corpus (corpus-authoring circularity) — optional program addition.
- ⚑ DANGLING_RULE contraction fix — schedule the v2-contractor build before any operator retest.

