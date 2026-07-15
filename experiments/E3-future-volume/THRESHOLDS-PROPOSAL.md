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

## Proposed values

| parameter | proposed | basis |
|---|---|---|
| `r2_fidelity_min` | **0.10** | No external anchor exists (negative finding above). 0.10 = "explains meaningfully more than nothing" at corpus scale (n≈200, d=3584, ridge); deliberately modest because the real discriminator is the margin clause below. Pilot-informed only in that the floor mass point argues against a high absolute bar. Sweep: {0.05, 0.10, 0.20}. |
| `r2_margin_over_classmean_min` | **0.05** | The clause that separates "reads a continuum" from "reads the binary class" (the SEP guard). 0.05 absolute R² over the class-mean oracle is small but non-noise at n≈200; the synthetic binary-only fixture failed this clause by −0.19, i.e. the clause has real teeth. Sweep: {0.05, 0.10}. |
| `r2_ood_min` | **0.05** | Transfer floor for the load-bearing leave-one-family-out regime. Set low deliberately: OOD transfer at ANY positive fidelity is the discriminating geometric claim; the shortcut fixture collapsed to −0.54, so even 0.05 separates transfer from shortcut collapse by construction. OOD/in-dist ratio co-reported descriptively. Sweep: {0.05, 0.10}. |
| `auc_binary_min` | **0.70** | Bottom of SEP's own 0.7–0.95 binarized-probing range; consistent with the 0.62–0.80 replication floor on this model class. Used only to distinguish refuted/binary-only from refuted/no-signal — it gates no confirmation. |
| `vc_ci_floor` | **0.0** | Strict beat: the 95% paired-bootstrap CI-low of (probe AUROC − verbalized AUROC) must exceed 0. With B1 expected at 0.50–0.70 on this model class and probe methods publishing 0.77–0.90, a genuine effect should clear a zero floor; anything softer would let noise "beat" the baseline. |
| ridge `alpha` grid | **logspace(10⁻², 10⁶, 9 points)** | Standard decade grid spanning under- to over-regularized at d=3584, n≈200; selected by inner 5-fold CV on train only (e3-0001). |
| inner CV folds | **5** | Convention; n≈160 train → ~32 per fold, adequate for alpha selection. |
| bootstrap resamples | **10,000** | Stable 95% CI tails at answerable-subset size (~126); cheap (CPU seconds). |
| CI level | **95% two-sided** | Program convention (α = 0.05, e3-0003 procedure). |

## How the sweeps work (pre-registered, not post-hoc)

The registered value of each swept parameter is the **primary**; the verdict is computed at the primary.
The sweep values are computed and reported alongside, and the write-up must state whether the verdict
branch is stable across the sweep. A verdict that flips inside its sweep band is reported as
**threshold-fragile** — a pre-registered honesty label, not a re-decision. No sweep value may be promoted
to primary after data exists (e3-0004 freeze boundary: that requires a new registration).

## What this proposal does not do

It does not decide. The registration decides, and that act is human. It also does not touch the verdict
*semantics* — the branch structure (confirmed-shaped; refuted/no-signal; refuted/binary-only;
refuted/ood-failure; refuted/no-margin-over-verbalized) is fixed by the E3 protocol's § Verdict conditions
and proven on planted fixtures (`VALIDATION.md`); only the numeric bars are open, and only they are
proposed here.
