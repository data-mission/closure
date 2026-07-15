# E3 verdict thresholds — proposal

**STATUS: PROPOSED. Binds nothing.** The verdict logic (`validation/src/e3_validation/verdict.py`)
deliberately takes every threshold as a parameter and invents no value; this document proposes the values
the OSF registration should fix. The decision is a human act at registration time. Every pilot-informed
number below is disclosed as pilot-informed, per the program's pilot-testing discipline; the pilot data is
disposable (`PILOT.md`) and no confirmatory datum exists as of this writing.

## Evidence base

Two sources, kept separate so their weights are auditable:

- **Literature anchors** (web-gathered 2026-07-14, `abstract-checked` per the citation ceiling — not
  `verified` until a named person reads the primary sources):
  - Semantic Entropy Probes (arXiv:2406.15927): probing the binarized SE class reaches AUROC **0.7–0.95**
    by layer/scenario (the paper's own prose range). Its correctness tables give only deltas vs an
    accuracy-probe baseline (−2.0 to +2.8pp in-distribution; +2.2 to +10.5pp on unseen tasks).
  - SEP-style replication on 3–8B models (arXiv:2603.21172, Table A2): correctness AUROC **0.62–0.80**.
  - Ridge uncertainty probes on 3–8B models (arXiv:2510.04108): AUROC **0.77–0.90**, beating sampled
    semantic entropy (0.79–0.84) and verbalized/reflexive methods (0.72–0.83) on open-ended TriviaQA.
  - Verbalized confidence, 7–8B instruct models (GrACE arXiv:2509.09438 Table 1 and the consistent
    2025–26 pattern): AUROC **~0.50–0.70**; the channel clusters in (0.9, 1.0] regardless of correctness.
  - Semantic Volume (arXiv:2502.21239, Table 3, TriviaQA-5K): volume AUROC **79.6** vs sampled semantic
    entropy 73.4.
  - **A negative finding that shapes this whole proposal:** no published work reports R²/Spearman for
    regressing a *continuous* uncertainty quantity from hidden states — the field's convention is
    binarized AUROC throughout. E3's R² bars therefore have **no external anchor to borrow**; they must
    be set modestly, justified by construction, and protected by pre-registered sensitivity sweeps.
- **Pilot observations** (30 disposable prompts, `PILOT.md` — plumbing facts, not results):
  - Volume dynamic range ≈ 124 log units with **zero overlap** between the low-diversity kind
    (instruction, all ≤ −107.7) and high-diversity kinds (ambiguous/creative, all ≥ −19.5).
  - **A floor mass point exists**: 6/30 prompts hit the exact degenerate minimum `10·log(1e-6) = −138.155`
    (all ten continuations semantically identical). The log-volume target is therefore mixed
    discrete-continuous at the bottom of its range. R² is sensitive to a mass point; Spearman is robust
    to it. This is why the fidelity criterion below keeps R² as the registered bar (it is the claim's
    natural scale) but requires Spearman to be co-reported, and why the sweep matters.
  - Verbalized confidence behaved exactly as the literature says (median 100, min 70 — near-uniform
    overconfidence; 0 parse failures), consistent with a beatable but non-trivial B1.

## Redesign note (e3-0005, 2026-07-14)

The audit-driven redesign (`decisions/e3-0005-audit-redesign.md`) changed the open set this document
proposes over. It **added** ten open parameters (precondition, two-part fidelity, within-family +
OOD-Spearman gates, added-value gates, length gate, out-of-fold folds), **retired** `r2_ood_min` (the
pooled-R² OOD bar is replaced by within-held-out-family Spearman bars), and **demoted**
`r2_margin_over_classmean_min` from a fidelity gate to B2 reporting only (the family-mean-oracle margin is
the gate now). The proposal below reflects the rebuilt instrument
(`validation/src/e3_validation/verdict.py`); every parameter name and default here matches
`VerdictThresholds` exactly. Values informed by the rehearsal (`REHEARSAL.md`) or the hardening calibration
(`hardening/HARDENING.md`) are disclosed as **pilot-material-informed**, on the same footing as the
spike/pilot disclosures — no number below is evidence for or against H-VOL.

## Proposed values

Pre-existing bars (carried from before the redesign, unchanged in role except where demoted):

| parameter | proposed | basis |
|---|---|---|
| `r2_fidelity_min` | **0.10** | No external anchor exists (negative finding above). 0.10 = "explains meaningfully more than nothing" at corpus scale (n≈200, d=3584, ridge); deliberately modest because the real discriminators are now the Spearman, within-family, and family-oracle-margin gates. Pilot-informed only in that the floor mass point argues against a high absolute bar. Now scored on the **non-degenerate subset** (two-part treatment). Sweep: {0.05, 0.10, 0.20}. |
| `r2_margin_over_classmean_min` | **0.05** *(DEMOTED — reporting only)* | Was the SEP fidelity guard; the redesign replaces it with `family_oracle_margin_min` as the gate and keeps this quantity as B2 reporting (`classmean_margin` in `verdict.py`). Value retained for the report. The synthetic binary-only fixture failed the old clause by −0.186, so the reported quantity still has interpretive teeth. Not a gate; not swept as a verdict-moving bar. |
| `auc_binary_min` | **0.70** | Bottom of SEP's own 0.7–0.95 binarized-probing range; consistent with the 0.62–0.80 replication floor on this model class. Used only to distinguish `refuted/binary-only` from `refuted/no-signal`/`refuted/margin-only` — it gates no confirmation. |
| `vc_ci_floor` | **0.0** | Strict beat: the 95% paired-bootstrap CI-low of the probe's AUROC margin over the **strongest** verbalized variant (max-over-verbalized) must exceed 0. With B1 expected at 0.50–0.70 on this model class and probe methods publishing 0.77–0.90, a genuine effect should clear a zero floor; anything softer would let noise "beat" the baseline. Rehearsal caveat: B1 took only two values (95, 100), so this margin is discreteness-fragile — the reason the B3 gate below was added. |
| ridge `alpha` grid | **logspace(10⁻², 10⁶, 9 points)** | Standard decade grid spanning under- to over-regularized at d=3584, n≈200; selected by inner 5-fold CV on train only (e3-0001). |
| inner CV folds | **5** | Convention; n≈160 train → ~32 per fold, adequate for alpha selection. |
| bootstrap resamples | **10,000** | Stable 95% CI tails at answerable-subset size (~126); cheap (CPU seconds). |
| CI level | **95% two-sided** | Program convention (α = 0.05, e3-0003 procedure). |

New bars added by the redesign (e3-0005; all previously unset — proposed here for the first time):

| parameter | proposed | basis |
|---|---|---|
| `min_negatives` | **15** | Precondition: below this many negatives in the answerable subset the correctness arm is `NOT_EVALUABLE`, not refuted (`preconditions.py`). The rehearsal fired `confirmed-shaped` on **one** negative; the calibration projects a ≈0.20–0.25 negative rate → ~25–32 negatives at 126 answerable, so 15 is a floor comfortably below the projection yet far above the fragile-arm regime. Rehearsal-informed; the rehearsal's own "≥ 20 negatives" note is the stricter alternative and a natural sweep point. Sweep: {15, 20}. |
| `spearman_fidelity_min` | **0.3** | Floor-mass-robust half of the two-part fidelity target: minimum Spearman on the non-degenerate subset (`fidelity.py`). Spearman is immune to the `10·log(ε)` floor mass point that inflates/deflates R² (pilot 6/30, rehearsal 11/41 on the floor); 0.3 is a modest monotone-signal floor, no external anchor (field reports binarized AUROC, not continuous Spearman). Sweep: {0.2, 0.3, 0.4}. |
| `within_family_spearman_min` | **0.3** | Kills the family-band confound: minimum within-family Spearman (volume/predictions residualized on train-derived family means), and the bar the length-residualized within-family Spearman must also clear. On rehearsal data between-family η² was 0.255 and ρ(volume, length) 0.910 — a global metric can pass on family/length structure alone, so a within-family floor is mandatory. **Note:** the instrument's throwaway routing fixture used 0.5 for this field only to route planted cases; that is not a proposal. 0.3 proposed here. Sweep: {0.2, 0.3, 0.4}. |
| `family_oracle_margin_min` | **0.05** | Replaces the 2-bin class-mean margin as the fidelity gate: minimum `probe R² − family-mean-oracle R²` (`fidelity.py`). The probe must beat the ceiling of purely between-family information; 0.05 absolute R² over that oracle is small but non-noise at n≈200. Sweep: {0.05, 0.10}. |
| `ood_pooled_spearman_min` | **0.2** | Load-bearing transfer bar: minimum pooled (mean-over-rotations) within-held-out-family Spearman (`ood.py`). Within-family rank correlation is immune to the between-family mean structure the old pooled-R² bar rewarded. Set modestly — transfer at any positive within-family rank signal is the geometric claim; the rehearsal's pooled LOFO Spearman was 0.667 but with `factual` transferring at only +0.060, which the per-family floor below is designed to catch. Sweep: {0.2, 0.3}. |
| `ood_per_family_floor` | **0.0** | No rotation may collapse: every per-rotation within-held-out-family Spearman must be ≥ this floor (`ood_min_rotation_spearman < ood_per_family_floor` → `REFUTED_OOD_FAILURE`). At 0.0 a single family collapsing to a negative within-family rank correlation refutes even if the pooled mean clears — the rehearsal's near-zero `factual` rotation (+0.060) is exactly the case this guards. Kept at the zero floor deliberately: any positive per-family requirement is stricter and swept. Sweep: {0.0, 0.1}. |
| `b3_ci_floor` | **0.0** | Probe must beat predictive entropy B3: the 95% paired-bootstrap CI-low of (probe − B3) AUROC margin must exceed 0 (`REFUTED_NO_MARGIN_OVER_ENTROPY`). Added because B3 is free (same forward pass), pilot ρ(volume, entropy) = 0.827, and the README confirmation clause never required beating it. Strict-beat floor mirrors `vc_ci_floor`. Sweep: {0.0}. |
| `b4_margin_ceiling` | **0.0** | The correctness probe B4 must not dominate the volume probe: (B4 − probe) AUROC-margin CI-low must be ≤ this ceiling (`REFUTED_DOMINATED_BY_CORRECTNESS_PROBE`). Anchored in arXiv:2509.10625 (B4 beating verbalized confidence on Qwen2.5-7B): a volume probe that adds nothing over directly probing correctness is refuted. 0.0 → B4's advantage must not exclude zero. Sweep: {0.0}. |
| `require_length_robust` | **true** | Enforce the length gate: within-family fidelity must survive residualizing volume on continuation length (mean+std) or the verdict is `REFUTED_LENGTH_CONFOUNDED`. Mandatory given rehearsal ρ(volume, mean length) = 0.910 (rank) — a `confirmed-shaped` verdict without this control is one "your probe reads verbosity" review from collapse (`PREMORTEM.md` §1). Not swept (a boolean gate). |
| `correctness_cv_folds` | **5** | Out-of-fold fold count for the strictly-OOF probe/B4 correctness scoring (`correctness.py`; no in-sample scoring path exists). 5 folds on the ~126-item answerable subset → ~25 held-out per fold, adequate for AUROC scoring without an in-sample leak. Convention, matching the inner-CV fold count. Sweep: {5, 10}. |

## How the sweeps work (pre-registered, not post-hoc)

The registered value of each swept parameter is the **primary**; the verdict is computed at the primary.
The sweep values are computed and reported alongside, and the write-up must state whether the verdict
branch is stable across the sweep. A verdict that flips inside its sweep band is reported as
**threshold-fragile** — a pre-registered honesty label, not a re-decision. No sweep value may be promoted
to primary after data exists (e3-0004 freeze boundary: that requires a new registration).

## What this proposal does not do

It does not decide. The registration decides, and that act is human. It also does not touch the verdict
*semantics* — the branch structure (the terminal `not-evaluable/correctness-arm`; `confirmed-shaped`; and
the refuted branches `no-signal`, `margin-only`, `binary-only`, `length-confounded`, `ood-range-uncovered`,
`ood-failure`, `no-margin-over-verbalized`, `no-margin-over-entropy`, `dominated-by-correctness-probe`) is
fixed by the E3 protocol's § Verdict conditions as refined by `decisions/e3-0005-audit-redesign.md`, and
proven on planted fixtures (`VALIDATION.md`); only the numeric bars are open, and only they are proposed
here.
