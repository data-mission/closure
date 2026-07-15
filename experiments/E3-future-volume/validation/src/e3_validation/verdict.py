"""Pre-registered verdict-branch logic (E3 README § Verdict conditions), audit-driven redesign.

The README fixes the two headline branches:

    CONFIRMED iff the probe regresses continuous volume with useful fidelity, generalizes OOD, and
    beats verbalized confidence on correctness prediction.
    REFUTED iff the signal exists only at binary granularity (already known from SEP), or fails OOD,
    or adds nothing over verbalized confidence.

The labeled dress rehearsal (REHEARSAL.md) fired the strongest branch (confirmed-shaped) off an
evidentially empty correctness arm — one negative in 41 items — because the branch logic had **no
guard on the mass of the correctness labels**, and because the fidelity clause read a family-band /
length confound rather than a within-family geometric quantity (ρ(volume, mean length) = 0.910 rank,
between-family η² of volume = 0.255). This module is the redesign that closes those holes.

The verdict is a function of **exactly** the quantities enumerated on ``VerdictInputs`` and no
others; every threshold is an open parameter carried on ``VerdictThresholds`` (this module invents
no numeric value — the registration fixes them, e3-0004 freeze). Decision precedence, top to bottom:

    0. PRECONDITION (preconditions.py). If the answerable subset carries fewer than
       ``min_negatives`` negatives, the correctness arm cannot be evaluated at all and the verdict is
       the terminal, honest ``NOT_EVALUABLE_CORRECTNESS_ARM`` — NOT a refutation. Checked before any
       branch, so no confirmation or refutation can rest on empty evidence.

    1. CONTINUOUS FIDELITY (fidelity.py), all four required, all on the NON-degenerate subset:
         r2_nondegenerate      >= r2_fidelity_min
         spearman_nondegenerate>= spearman_fidelity_min
         within_family_spearman>= within_family_spearman_min   (kills the family-band confound)
         family_oracle_margin  >= family_oracle_margin_min      (probe beats the family-mean oracle)
       The old 2-bin class-mean margin (``r2_indist - r2_classmean_indist``) is retained only as
       B2-related REPORTING; the family-mean-oracle margin is the gate that replaces it.

       If fidelity holds:
         1a. LENGTH GATE (param-gated). Within-family fidelity must ALSO survive residualizing the
             volume on continuation length (mean+std). If ``require_length_robust`` and the
             length-residualized within-family Spearman falls below ``within_family_spearman_min``,
             the fidelity was a verbosity readout -> REFUTED_LENGTH_CONFOUNDED.
         1b. OOD RANGE (ood.py). If any leave-one-family-out rotation's held-out true-volume range
             is not covered by the training range, the held-out family is an extrapolation, not a
             transfer test -> REFUTED_OOD_RANGE_UNCOVERED (distinct from a genuine collapse).
         1c. OOD TRANSFER (ood.py). Pooled (mean-over-rotations) within-held-out-family Spearman and
             every per-rotation Spearman must clear their bars -> else REFUTED_OOD_FAILURE.
         1d. ADDED VALUE over the baselines (compare.py paired bootstrap). OOD is resolved BEFORE the
             verbalized/added-value gates (OOD-before-VC precedence): a probe that collapses OOD is
             refuted on OOD even if it would have beaten verbalized confidence. Then, in order:
               probe beats verbalized (all B1 variants) : probe_vs_vc_ci_low > vc_ci_floor
               probe beats predictive entropy (B3)      : probe_vs_b3_ci_low > b3_ci_floor
               correctness probe (B4) does NOT beat it  : b4_vs_probe_ci_low <= b4_margin_ceiling
             Failing each routes to a DISTINCT honest branch (no conflation): respectively
             REFUTED_NO_MARGIN_OVER_VERBALIZED, REFUTED_NO_MARGIN_OVER_ENTROPY,
             REFUTED_DOMINATED_BY_CORRECTNESS_PROBE.
         Otherwise -> CONFIRMED_SHAPED.

    2. NO FIDELITY. Then:
         auc_binary >= auc_binary_min                 -> REFUTED_BINARY_ONLY   (already known from SEP)
         else r2_nondegenerate >= r2_fidelity_min      -> REFUTED_MARGIN_ONLY   (above-floor R^2 that
             fails the margin/within-family gates AND shows no binarized signal — this is the row the
             pre-redesign code mislabeled ``refuted/no-signal``)
         else                                          -> REFUTED_NO_SIGNAL
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from . import preconditions


class Verdict(str, Enum):
    """The pre-registered verdict branches (audit-driven redesign)."""

    # Terminal precondition state — honest "cannot decide", not a refutation.
    NOT_EVALUABLE_CORRECTNESS_ARM = "not-evaluable/correctness-arm"

    CONFIRMED_SHAPED = "confirmed-shaped"

    # Fidelity present but does not survive a robustness or added-value gate.
    REFUTED_LENGTH_CONFOUNDED = "refuted/length-confounded"
    REFUTED_OOD_RANGE_UNCOVERED = "refuted/ood-range-uncovered"
    REFUTED_OOD_FAILURE = "refuted/ood-failure"
    REFUTED_NO_MARGIN_OVER_VERBALIZED = "refuted/no-margin-over-verbalized"
    REFUTED_NO_MARGIN_OVER_ENTROPY = "refuted/no-margin-over-entropy"
    REFUTED_DOMINATED_BY_CORRECTNESS_PROBE = "refuted/dominated-by-correctness-probe"

    # No continuous fidelity.
    REFUTED_BINARY_ONLY = "refuted/binary-only"
    REFUTED_MARGIN_ONLY = "refuted/margin-only"
    REFUTED_NO_SIGNAL = "refuted/no-signal"


@dataclass(frozen=True)
class VerdictThresholds:
    """Decision thresholds — fixed by the registration, NOT by this code (e3-0004 freeze).

    Every field is an open parameter the pre-registration sets before any real datum exists. The
    synthetic stage supplies throwaway values only to route planted fixtures. Fields marked NEW were
    added by the audit-driven redesign; the open set is enumerated in VALIDATION.md.

    Fields:
        min_negatives: minimum number of negatives (incorrect-labeled answerable items) required for
            the correctness arm to be evaluable at all (NEW; precondition layer). Below it the verdict
            is NOT_EVALUABLE_CORRECTNESS_ARM.
        r2_fidelity_min: minimum held-out R^2 on the NON-degenerate subset for "continuous fidelity".
        spearman_fidelity_min: minimum held-out Spearman on the NON-degenerate subset (NEW; the
            floor-mass-point-robust half of the two-part fidelity target).
        within_family_spearman_min: minimum within-family Spearman (volume residualized on train-
            derived family means) for fidelity, and the bar the length-residualized within-family
            Spearman must also clear (NEW; kills the family-band and length confounds).
        family_oracle_margin_min: minimum ``probe_r2 - family_mean_oracle_r2`` (NEW; the probe must
            beat the family-mean oracle, replacing the 2-bin class-mean guard as the fidelity gate).
        r2_margin_over_classmean_min: the old 2-bin class-mean margin bar. RETAINED for B2-related
            reporting only; no longer a fidelity gate.
        ood_pooled_spearman_min: minimum pooled (mean over rotations) within-held-out-family Spearman
            (NEW; the leave-one-family-out transfer bar — a within-family rank correlation immune to
            between-family mean structure, replacing the pooled-R^2 OOD bar).
        ood_per_family_floor: minimum within-held-out-family Spearman EVERY rotation must clear (NEW;
            a single collapsing rotation refutes even if the pooled mean clears).
        auc_binary_min: minimum SEP-style median-split AUROC for "a binarized signal exists" (B2).
        vc_ci_floor: probe beats verbalized confidence iff the paired-bootstrap CI-low of the
            (probe minus WORST verbalized variant) AUROC margin exceeds this floor.
        b3_ci_floor: probe beats predictive entropy (B3) iff the paired-bootstrap CI-low of the
            (probe minus B3) AUROC margin exceeds this floor (NEW).
        b4_margin_ceiling: the correctness probe (B4) does NOT significantly beat the probe iff the
            paired-bootstrap CI-low of the (B4 minus probe) AUROC margin is at or below this ceiling
            (NEW; default 0.0 -> B4's advantage does not exclude zero).
        require_length_robust: whether the length gate is enforced (NEW; param-gated per the spec).
    """

    min_negatives: int
    r2_fidelity_min: float
    spearman_fidelity_min: float
    within_family_spearman_min: float
    family_oracle_margin_min: float
    r2_margin_over_classmean_min: float
    ood_pooled_spearman_min: float
    ood_per_family_floor: float
    auc_binary_min: float
    vc_ci_floor: float = 0.0
    b3_ci_floor: float = 0.0
    b4_margin_ceiling: float = 0.0
    require_length_robust: bool = True


@dataclass(frozen=True)
class VerdictInputs:
    """The measured quantities the branch logic consumes — the verdict is a function of EXACTLY
    these and nothing else.

    Precondition:
        n_negatives: count of negatives in the answerable subset (feeds the min_negatives guard).

    Two-part continuous-fidelity target (non-degenerate subset; degenerate = volume within tolerance
    of the ``N*log(epsilon)`` floor, split out by fidelity.py):
        r2_nondegenerate: held-out R^2 of the ridge probe on the non-degenerate subset.
        spearman_nondegenerate: held-out Spearman on the non-degenerate subset.
        n_nondegenerate, n_degenerate: subset sizes (reporting).
        degeneracy_auroc: AUROC of the separately-reported degeneracy classifier (logistic on the
            hidden state predicting the degenerate-floor indicator); reported, not gated.

    Within-family fidelity (family-band confound guard):
        within_family_spearman: Spearman of probe vs volume, both residualized on train-derived
            family means (rank correlation inside families).
        within_family_r2: the R^2 counterpart (reporting).
        family_oracle_r2: R^2 of the family-mean oracle (predict each item by its family's train
            mean) — the ceiling of purely between-family information (reporting).
        family_oracle_margin: ``probe_r2 - family_oracle_r2`` (the gated margin).

    Length gate:
        within_family_spearman_length_resid: within-family Spearman after ALSO residualizing volume
            on mean+std continuation length.

    B2-related reporting (retained from the pre-redesign contract):
        r2_indist: held-out R^2 on the full in-distribution subset (incl. degenerate).
        r2_classmean_indist: R^2 of the 2-bin class-mean oracle (SEP binarized ceiling).
        auc_binary: SEP-style median-split logistic AUROC (B2).

    OOD (leave-one-family-out, ood.py):
        ood_pooled_spearman: mean over rotations of within-held-out-family Spearman.
        ood_min_rotation_spearman: the minimum such Spearman over rotations.
        ood_range_uncovered: True iff any rotation's held-out true-volume range is not covered by the
            training range (extrapolation, not transfer).

    Added value on correctness prediction (compare.py paired bootstrap; probe/B4 scored out-of-fold):
        probe_vs_vc_ci_low: paired-bootstrap CI-low of the (probe minus WORST verbalized variant)
            AUROC margin — beating this beats the strongest verbalized arm supplied.
        probe_vs_b3_ci_low: paired-bootstrap CI-low of the (probe minus B3 entropy) AUROC margin.
        b4_vs_probe_ci_low: paired-bootstrap CI-low of the (B4 minus probe) AUROC margin.
    """

    n_negatives: int

    r2_nondegenerate: float
    spearman_nondegenerate: float
    n_nondegenerate: int
    n_degenerate: int
    degeneracy_auroc: float

    within_family_spearman: float
    within_family_r2: float
    family_oracle_r2: float
    family_oracle_margin: float

    within_family_spearman_length_resid: float

    r2_indist: float
    r2_classmean_indist: float
    auc_binary: float

    ood_pooled_spearman: float
    ood_min_rotation_spearman: float
    ood_range_uncovered: bool

    probe_vs_vc_ci_low: float
    probe_vs_b3_ci_low: float
    b4_vs_probe_ci_low: float


def has_continuous_fidelity(inputs: VerdictInputs, thresholds: VerdictThresholds) -> bool:
    """True iff all four continuous-fidelity gates clear on the non-degenerate subset: R^2, Spearman,
    within-family Spearman (family-band confound guard), and the family-mean-oracle margin. The old
    class-mean margin is reporting only and is deliberately NOT part of this predicate."""
    return (
        inputs.r2_nondegenerate >= thresholds.r2_fidelity_min
        and inputs.spearman_nondegenerate >= thresholds.spearman_fidelity_min
        and inputs.within_family_spearman >= thresholds.within_family_spearman_min
        and inputs.family_oracle_margin >= thresholds.family_oracle_margin_min
    )


def classmean_margin(inputs: VerdictInputs) -> float:
    """The retained 2-bin class-mean margin (B2 reporting): ``r2_indist - r2_classmean_indist``."""
    return inputs.r2_indist - inputs.r2_classmean_indist


def decide(inputs: VerdictInputs, thresholds: VerdictThresholds) -> Verdict:
    """Return the pre-registered verdict branch. See the module docstring for the full precedence.

    Precedence is load-bearing and audited: the precondition is checked before any branch (no verdict
    rests on empty correctness evidence), and OOD is resolved before the verbalized/added-value gates.
    """
    # 0. Precondition — the correctness arm must carry evidential mass.
    if not preconditions.correctness_arm_evaluable(inputs.n_negatives, thresholds.min_negatives):
        return Verdict.NOT_EVALUABLE_CORRECTNESS_ARM

    if has_continuous_fidelity(inputs, thresholds):
        # 1a. Length gate (param-gated): within-family fidelity must survive length residualization.
        if (
            thresholds.require_length_robust
            and inputs.within_family_spearman_length_resid < thresholds.within_family_spearman_min
        ):
            return Verdict.REFUTED_LENGTH_CONFOUNDED

        # 1b. OOD range coverage — extrapolation is not a transfer test.
        if inputs.ood_range_uncovered:
            return Verdict.REFUTED_OOD_RANGE_UNCOVERED

        # 1c. OOD transfer (pooled AND every rotation). Resolved BEFORE the added-value gates.
        if (
            inputs.ood_pooled_spearman < thresholds.ood_pooled_spearman_min
            or inputs.ood_min_rotation_spearman < thresholds.ood_per_family_floor
        ):
            return Verdict.REFUTED_OOD_FAILURE

        # 1d. Added value over the baselines — distinct honest branches, no conflation.
        if inputs.probe_vs_vc_ci_low <= thresholds.vc_ci_floor:
            return Verdict.REFUTED_NO_MARGIN_OVER_VERBALIZED
        if inputs.probe_vs_b3_ci_low <= thresholds.b3_ci_floor:
            return Verdict.REFUTED_NO_MARGIN_OVER_ENTROPY
        if inputs.b4_vs_probe_ci_low > thresholds.b4_margin_ceiling:
            return Verdict.REFUTED_DOMINATED_BY_CORRECTNESS_PROBE

        return Verdict.CONFIRMED_SHAPED

    # 2. No continuous fidelity.
    if inputs.auc_binary >= thresholds.auc_binary_min:
        return Verdict.REFUTED_BINARY_ONLY
    if inputs.r2_nondegenerate >= thresholds.r2_fidelity_min:
        # Above the R^2 floor but denied by the margin / within-family gates, with no binarized
        # signal either. The pre-redesign code mislabeled this row ``refuted/no-signal``.
        return Verdict.REFUTED_MARGIN_ONLY
    return Verdict.REFUTED_NO_SIGNAL


def branch_report(inputs: VerdictInputs, thresholds: VerdictThresholds) -> Mapping[str, object]:
    """A flat, JSON-friendly record of the verdict and every gate outcome — the honest audit trail
    the rehearsal showed was missing (which clause fired, on what evidential mass)."""
    return {
        "verdict": decide(inputs, thresholds).value,
        "n_negatives": inputs.n_negatives,
        "min_negatives": thresholds.min_negatives,
        "correctness_arm_evaluable": preconditions.correctness_arm_evaluable(
            inputs.n_negatives, thresholds.min_negatives
        ),
        "has_continuous_fidelity": has_continuous_fidelity(inputs, thresholds),
        "classmean_margin_reporting": classmean_margin(inputs),
        "family_oracle_margin": inputs.family_oracle_margin,
        "within_family_spearman": inputs.within_family_spearman,
        "within_family_spearman_length_resid": inputs.within_family_spearman_length_resid,
        "ood_pooled_spearman": inputs.ood_pooled_spearman,
        "ood_min_rotation_spearman": inputs.ood_min_rotation_spearman,
        "ood_range_uncovered": inputs.ood_range_uncovered,
        "degeneracy_auroc": inputs.degeneracy_auroc,
        "n_degenerate": inputs.n_degenerate,
        "n_nondegenerate": inputs.n_nondegenerate,
    }
