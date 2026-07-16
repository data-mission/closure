# E5 — VERDICT (filled at S5, 2026-07-16)

STATUS: FILLED from the registered run of 2026-07-15/16. Confirmatory blocks quote the
pre-registered conditions VERBATIM from `~/repos/closure/experiments/E5-reclosure/README.md`
("Verdict conditions (pre-registered)"). Every number below is measured from
`E5-CORPUS/arms-scores.jsonl` (180 rows) / `results-summary.json`; all three z-tests were
independently recomputed by hand — exact match to the frozen `stats.py`.

Config hash (matches the registered token):
`6dbe47a8e843ec1540f64ed6ddd8339c17b95688db363e31605502e374a8b9f0`
Registration record: freeze-by-public-commit (this run's registration mechanism; the
amendment is recorded in PROTOCOL.md, "Pre-registration record") —
corpus `5deb8eb` 15:11:40Z + Arm-B `379c767` 15:25:40Z public on origin BEFORE first
generation 15:28:29Z; chain in `GATE-RECORD.md` (copied into this run folder). Result commit: the commit introducing this run folder.

---

## 0. Run manifest

- torch `2.13.0` / transformers `5.13.1` (harness `uv.lock`); NLI revision
  `b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7`, `use_fallback=False`; weight file
  (`model.safetensors`) sha256 `c03cd208bf920b4fbbb182a0535859a566e8acc3477d2b536bf87b769978524b`.
- device: `cpu` (registered) · config_hash matches registered token: **yes** (asserted on all
  180 score rows and 180 log rows).
- Registration gate passed: **yes**, in the amended freeze-by-public-commit form
  (GATE-RECORD.md; manual gate, lean driver `run_arms.py` — deviation §4.2).
- Tasks entering the arms: **60** (20/20/20 F1/F2/F3).
- Error draws per arm: A **0** · B **0** (arms-log.jsonl contains zero error rows).
- Tasks with no usable draw in some arm: **0**.
- Claim-level sanitation register (§9e, symmetric, pre-scoring): 9 arm-outputs touched,
  A×5 / B×4 claims stripped for invalid source indices — full register in results-summary.json.

## 1. NOT-RUNNABLE rail

No condition fired: 60/60 tasks, exact 20/20/20 balance, gate passed, hash matches, all arms
fully drawn. The experiment IS a registered run; §2 is filled.

## 2. CONFIRMATORY verdict

Primary numbers (pooled must-change items, N = 107 per arm after the 26-item pruning register):
- Contamination: **A 3/107 = 2.80% · B 1/107 = 0.93% · C 11/107 = 10.28%**
- B vs C: z = −2.9713, p = 0.002966, Bonferroni-corrected p = **0.008897 — significant**,
  direction: **C WORSE than B**.
- A vs B: z = 1.0095, corrected p = 0.938 — not significant (value-of-instruction not
  established at this baseline; the naive baseline floors near zero).
- A vs C: z = −2.2117, p = 0.026990, corrected p = 0.080971 — **not significant** after
  correction (the "worse than doing nothing" reading is directional only).
- Completeness (mean): B **0.9417** · C **0.9917** · diff (C − B) = **+0.0500** ·
  non-inferior (C ≥ B − 0.10): **yes** (C is nominally higher; no win-by-deletion).
- MDE around the B baseline (frozen formula, power 0.80, corrected α). The registered text
  says "N = 60" (tasks); the pinned unit of analysis (§6a) is pooled items, N = 107/arm. Both
  are reported rather than choosing the favorable one: **0.0426 absolute at N = 107 items**,
  **0.0568 absolute at N = 60** — the observed B→C gap (0.0935) exceeds both (2.2× / 1.6×).

### Which pre-registered block fires

- ☐ CONFIRMED — does NOT fire: C does not beat B (C is significantly worse).
- ☐ CONTRACTION WINS BY DELETION — does NOT fire: requires C lower on contamination.
- ☒ **REFUTED** — the operative consequence fires: "instruction suffices in this setting …
  and the `release` operator is demoted in the registry." **Disclosed wording gap:** the
  registered REFUTED wording says "B ≈ C … does NOT clear the significance threshold (no
  significant separation)", but the observed separation IS significant — in the direction
  OPPOSITE to H-RELEASE. The three registered blocks did not enumerate a significant reversal.
  Adjudication: the reversal is strictly stronger evidence against H-RELEASE than the
  registered REFUTED condition; the verdict is recorded as **REFUTED (in stronger-than-registered
  form)** and the non-exhaustive condition space is logged as a pre-registration defect, not
  absorbed. No block is claimed as fitting when it does not.

`release` as formulated is demoted in the registry. The mechanical contraction operator did not
merely fail to beat a one-paragraph instruction — it injected contamination the instruction
avoids (10.28% vs 0.93%), while an appended correction alone already achieves 2.80%.

### Validity gate

Affirmed: Arm C was constructed exclusively via `contraction.contract()` (run_arms.py phase 2),
uniform across tasks, no per-task hand-authored path. Bit-for-bit regeneration check
(re-derive C from sanitized A outputs at frozen thresholds, compare logged `serialized_sha256`):
**60/60 match** (`c-regeneration-check.json`, 2026-07-16T06:02Z).

### Effect sizes per task family

| Family | A cont. | B cont. | C cont. | B−C diff | note |
|---|---|---|---|---|---|
| F1 (direct/procedural) | 3/35 = 8.6% | 1/35 = 2.9% | 7/35 = 20.0% | −17.1pp | verdict-style conclusions: where contraction misfires hardest |
| F2 (second-order/synthesis) | 0/32 = 0.0% | 0/32 = 0.0% | 4/32 = 12.5% | −12.5pp | literature predicted largest B-fail here; observed B-fail = zero |
| F3 (mixed/quantitative) | 0/40 = 0.0% | 0/40 = 0.0% | 0/40 = 0.0% | 0 | contraction handles parametric claims cleanly; family carries no signal |

Per contamination depth (`depth-table.json`; per-item rescore whose per-(task,arm) aggregates
reproduced every banked score row exactly — 681 items, 0 mismatches):

| Depth | A cont. | B cont. | C cont. |
|---|---|---|---|
| direct | 3/56 = 5.4% | 1/56 = 1.8% | 7/56 = 12.5% |
| second_order | 0/51 = 0.0% | 0/51 = 0.0% | 4/51 = 7.8% |

All residual contamination in arms A and B sits on direct restatements; both keep zero stale
second-order inferences. Arm C is the only arm that contaminates the second-order layer at all.

## 3. EXPLORATORY (zero verdict weight)

- **Task-level robustness read (registered clustering companion, PROTOCOL §6a): AGREES.**
  Paired per-task contamination B vs C: C worse on 9 tasks, B worse on 0, ties 51; exact
  two-sided sign test p = 0.0039; mean per-task diff (C−B) = +0.083. The pooled confirmatory
  result is not a pooling artifact.
- **Sensitivity sweep** (9-point grid, `sensitivity-sweep.json`): the verdict is
  threshold-robust. C loses at ALL 9 cells: C = 11/107 at six cells, 12/107 at the three
  strictest-floor cells (0.75/*) — stricter thresholds make contraction worse, not better.
  B-vs-C significant at every cell (corrected p ≤ 0.0089); C completeness 0.992 at every cell.
  The frozen point (0.70/0.10) reproduces the registered 11/107 exactly.
- One task (F1-0016) is contaminated at 1.0 in ALL three arms — the model errs on it even
  before the correction, so it adds equal noise to every arm. No pre-registered rule excludes
  it; it stays in the 107 trials and is named here (flagged by the corpus audit).
- **Cross-vendor replication (S5b):** not yet run (gpt-5.4-mini-2026-03-17; needs OpenAI key).
- Observed patterns:
  - B's mean completeness (0.9417) sits below A's (0.9500) — a mild over-revision signal from
    the strong instruction; C's is highest (0.9917) because contraction deletes little that the
    persist set covers.
  - C's retained contamination concentrates in F1/F2 verdict-style conclusions: the contraction
    removes parametric/decorative claims but keeps superseded qualitative verdicts — the v2
    design insight (true AGM-style retraction of conclusions, not claim-list pruning).
  - The commissioned hostile corpus audit (2026-07-16) bounds the claim:
    baseline floors near zero (F2/F3 A-arm = 0.000), must_persist items are largely source
    echoes (completeness is a floor, not a test), reasoning depth is 1–2 ops. **Scope:** this
    run measures contraction-operator behavior on shallow document-revision tasks; it says
    nothing about revision under multi-hop reasoning. Verdict unaffected (audit: corpus
    "competent, correct, honestly-constructed, shallow"; arithmetic 91/91 correct; zero
    viral-puzzle contamination).

## 4. Deviations from the registered protocol

1. Registration by freeze-by-public-commit instead of an OSF deposit (GATE-RECORD.md; the
   amendment is recorded in PROTOCOL.md's pre-registration section).
2. Lean driver `run_arms.py` with a manually executed freeze gate instead of the
   in-code-gated `run_e5.py`; the gate is verifiable post-hoc (GATE-RECORD.md).
3. §9e claim-level sanitation repair, applied pre-scoring, arm-symmetric, disclosed in PROTOCOL.
4. Phase-4 crash (numpy-bool JSON serialization) AFTER all scoring: results-summary.json
   regenerated from raw score rows via the frozen stats functions; independent hand
   recomputation matched exactly. No datum recomputed, no generation re-run, $0.
5. Per-depth effect table + sensitivity sweep + Arm-C regeneration check computed 2026-07-16
   (CPU-only, no new generations), AFTER the confirmatory verdict was locked from the banked
   scores. The rescorer memoizes directional NLI pair-scores (11,752 unique pairs serving
   144,884 lookups) under the unmodified frozen harness functions; exactness gates (strict ==
   against direct scorer calls, 100+200 pairs, 0 diffs) and the full per-item cross-check
   (every banked (task,arm) aggregate reproduced exactly) precede any artifact write.
6. F3 short-context stratum exploratory-only (S3e quota relaxation per spec §10, disclosed).

Total run spend: ~$8.5 across pilot and arms (API generation costs only; scoring is local CPU).
