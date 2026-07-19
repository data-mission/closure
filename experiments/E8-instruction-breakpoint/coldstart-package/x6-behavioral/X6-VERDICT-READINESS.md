# X6 — verdict readiness (fires on pilot-completion tripwire)

Status 2026-07-19: **STAGED + TESTED against dry-run AND adversarial bad-data.** The verdict step is a
fixed 3-command chain with NO post-hoc discretion. Team-lead runs it on the completion tripwire.

## The chain (run in order the moment `results.jsonl` is complete)

```
cd ~/repos/closure/harness
R=~/e8-run/x6/results.jsonl           # completed pilot generation (280 rows: 40 fam × 2 arms × 3 doses + 40 D-EXC)
P="PYTHONPATH=~/e8-driver HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python"

# STEP 1 — ACCEPTANCE GATE (instrument validity; exits non-zero => WITHHOLD, do NOT proceed to verdict)
$P ~/e8-driver/x6_acceptance.py --results $R --out ~/e8-run/x6/x6-acceptance.json
#   exit 0 => PROCEED ; exit 2 => WITHHOLD -> X-HUMAN (positive-control miss, or TT cell, or incoherent
#   BLANKET curve). Read x6-acceptance.json for which gate fired.

# STEP 2 — DERIVE θ/δ from the pilot floor (frozen formula, prints every input)
$P ~/e8-driver/x6_derive_thresholds.py --results $R --out ~/e8-run/x6/x6-thresholds.json
#   reads theta/delta out of x6-thresholds.json for step 3.

# STEP 3 — VERDICT with the derived thresholds
THETA=$(python3 -c "import json;print(json.load(open('$HOME/e8-run/x6/x6-thresholds.json'))['theta'])")
DELTA=$(python3 -c "import json;print(json.load(open('$HOME/e8-run/x6/x6-thresholds.json'))['delta'])")
$P ~/e8-driver/x6_verdict.py --results $R --theta $THETA --delta $DELTA --out ~/e8-run/x6/x6-verdict.json
```

Verdict tags (x6_verdict.py): `SCOPE_LEAK` (separable break: mono gate + crossing + p_over−p_decay≥δ with
paired sig) / `DEGRADES_BUT_NOT_SEPARABLE` (collapses to SRD-class decay) / `NO_BREAK` / status `WITHHELD`
(any FF-ceiling / TT / cross-mismatch / pc-fail). These map 1:1 to the pre-stated two-sided conclusions
(X6-DESIGN §8).

## θ/δ derivation — the FROZEN formula (no discretion; documented in x6_derive_thresholds.py header)

Both use ONLY measured pilot inputs + four constants frozen BEFORE the pilot completes
(THETA_MIN=0.05, DELTA_MIN=0.03, THETA_FLOOR_MULT=5, DELTA_SD_MULT=2). No branch depends on the SCOPED
top-dose result — no fishing.

- **θ = max(5 × f_scoped1, 0.05)** where `f_scoped1` = SCOPED over-generalization rate at DOSE 1
  (guard-D conditioned). Mirrors PHASE0 §3's contamination-θ ("≈5× the measured floor — a crossing can't
  be noise off the floor"); falls back to the 0.05 absolute anti-noise floor (E8's contamination value)
  if the dose-1 floor is ~0.
- **δ = max(2 × sd_blanket_top, 0.03)** where `sd_blanket_top = sqrt(p(1−p)/n)` is the binomial SE of the
  BLANKET decay rate at the TOP dose. 2× the control's own sampling-noise band = the SCOPED excess must
  clear twice the BLANKET arm's noise before it counts as separable (the "larger than the BLANKET noise
  band" rule, X6-DESIGN §1b); floors at 0.03 so a near-zero-variance (immune-like) BLANKET arm still
  demands a real separation.

The output JSON reports `theta_binding`/`delta_binding` (floor-driven vs MIN-driven) so the reader sees
which term bound each threshold.

## Acceptance checks (STEP 1) — what each gate proves + TESTED to fire

- **AC1 positive controls fired** (guard B): every task's synthetic correct-in-unusual-form control must
  have A_correct fire; rate must = 1.0. A miss => the oracle is too narrow for real output => can't trust
  the FF/over counts. **Tested: fires (WITHHOLD) on a seeded miss.**
- **AC2 FF/TT within ceiling**: FF_rate ≤ 0.05 of SCOPED scored; TT = 0. Over => oracle didn't anticipate
  the real action space => X-HUMAN. **Tested: fires on a seeded TT cell.**
- **AC3 SRD-gap reproduction** on the BLANKET arm: the BLANKET decay curve must be monotone NON-DECREASING
  across dose (within 0.02 tol). We do NOT assert SRD's 73→33 magnitude (claude-sonnet-5 wasn't in SRD's
  12; the floor is model-specific — could be susceptible-like OR immune-like, both valid). We assert only
  DIRECTION-COHERENCE: decay may rise with turns (SRD-susceptible-like) or stay flat (immune-like), but a
  DECREASING curve would make the control incoherent and the paired contrast unsound => fail. The observed
  curve is reported alongside SRD's verified anchor for the writeup. **Tested: passes an increasing curve
  (labeled susceptible-like), passes a flat curve (immune-like), FAILS a decreasing curve.**

## Test evidence (all zero-spend, run on the Mini)
- Both scripts run clean on the 280-row pilot DRY-RUN: derivation → θ=0.05/δ=0.03 (both MIN-bound, correct
  for the zero-floor fixture); acceptance → AC1 280/280, AC2 0 FF/0 TT, AC3 flat/immune, gate PROCEED.
- Adversarial negative test (`x6_acceptance_negtest.py`, on Mini): AC1 fires on pc-miss, AC2 fires on TT,
  AC3 fires on a decreasing BLANKET curve and correctly passes an increasing one. Gates are NOT false-green.

## Note
- These operate on the SAME result shape the aggregator/verdict consume; no new scoring, no model, all
  deterministic. If STEP 1 withholds, STEP 2/3 still run (numbers computed for disclosure) but the verdict
  is not final until the flagged gate is X-HUMAN-adjudicated.
- The `--out` files (x6-acceptance.json, x6-thresholds.json, x6-verdict.json) are the durable record.
