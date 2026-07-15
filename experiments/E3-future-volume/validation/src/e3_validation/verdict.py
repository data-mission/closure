"""Pre-registered verdict-branch logic (E3 README § Verdict conditions).

The README fixes the branches:

    CONFIRMED iff the probe regresses continuous volume with useful fidelity, generalizes OOD, and
    beats verbalized confidence on correctness prediction.
    REFUTED iff the signal exists only at binary granularity (already known from SEP), or fails OOD,
    or adds nothing over verbalized confidence.

This module decides which branch a run lands in. It is parameterized entirely by
``VerdictThresholds`` — **this code invents no threshold value**. The registration fixes the
numbers (e3-0004 freeze boundary); the synthetic tests pass in throwaway thresholds chosen only to
route each planted fixture to its known-correct branch. The five distinguished branches:

    confirmed-shaped                 — continuous fidelity AND OOD transfer AND beats verbalized conf.
    refuted/no-signal                — no continuous fidelity and no binarized signal either.
    refuted/binary-only              — the binarized (median-split) AUROC clears its bar while the
                                       continuous probe does NOT exceed a class-mean predictor
                                       (the "already known from SEP" branch).
    refuted/ood-failure              — continuous fidelity in-distribution, but OOD (leave-one-family-
                                       out) collapses.
    refuted/no-margin-over-verbalized — continuous fidelity and OOD transfer present, but the probe
                                       does not beat verbalized confidence (paired-bootstrap CI on
                                       the AUROC margin does not clear the floor).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    """The pre-registered verdict branches."""

    CONFIRMED_SHAPED = "confirmed-shaped"
    REFUTED_NO_SIGNAL = "refuted/no-signal"
    REFUTED_BINARY_ONLY = "refuted/binary-only"
    REFUTED_OOD_FAILURE = "refuted/ood-failure"
    REFUTED_NO_MARGIN_OVER_VERBALIZED = "refuted/no-margin-over-verbalized"


@dataclass(frozen=True)
class VerdictThresholds:
    """Decision thresholds — fixed by the registration, NOT by this code.

    Every field is an open parameter that the pre-registration will set before any real datum
    exists (e3-0004 freeze). The synthetic stage supplies throwaway values only to route planted
    fixtures.

    Fields:
        r2_fidelity_min: minimum in-distribution R^2 for "continuous fidelity present".
        r2_margin_over_classmean_min: minimum ``r2_indist - r2_classmean_indist`` for the continuous
            probe to count as reading more than the binarized class (guards the binary-only branch).
        r2_ood_min: minimum leave-one-family-out R^2 for "OOD transfer present".
        auc_binary_min: minimum SEP-style median-split AUROC for "a binarized signal exists".
        vc_ci_floor: the probe beats verbalized confidence iff the paired-bootstrap CI **low** on the
            AUROC margin (probe minus verbalized) exceeds this floor (default 0.0 => CI excludes zero
            on the positive side).
    """

    r2_fidelity_min: float
    r2_margin_over_classmean_min: float
    r2_ood_min: float
    auc_binary_min: float
    vc_ci_floor: float = 0.0


@dataclass(frozen=True)
class VerdictInputs:
    """The measured quantities the branch logic consumes.

    Fields:
        r2_indist: in-distribution held-out R^2 of the continuous ridge probe.
        r2_classmean_indist: R^2 of the oracle class-mean predictor on the same in-distribution
            eval (the ceiling of binarized-only information).
        r2_ood: leave-one-family-out R^2 of the continuous ridge probe (aggregated over rotations).
        auc_binary: SEP-style median-split logistic AUROC (B2 of e3-0003).
        probe_vs_vc_ci_low: paired-bootstrap CI low of the AUROC margin (probe minus verbalized
            confidence) on correctness prediction (compare.paired_bootstrap_auroc_diff).
    """

    r2_indist: float
    r2_classmean_indist: float
    r2_ood: float
    auc_binary: float
    probe_vs_vc_ci_low: float


def has_continuous_fidelity(inputs: VerdictInputs, thresholds: VerdictThresholds) -> bool:
    """True iff the continuous probe both clears the in-dist R^2 bar and materially exceeds the
    class-mean predictor. The second clause is what separates a genuine continuous read from the
    binary-only case SEP already established."""
    clears_bar = inputs.r2_indist >= thresholds.r2_fidelity_min
    beats_classmean = (
        inputs.r2_indist - inputs.r2_classmean_indist
    ) >= thresholds.r2_margin_over_classmean_min
    return clears_bar and beats_classmean


def decide(inputs: VerdictInputs, thresholds: VerdictThresholds) -> Verdict:
    """Return the pre-registered verdict branch for a run's measured inputs.

    Branch order (pre-registered):
      1. If continuous fidelity is present (clears R^2 AND beats class-mean):
         a. OOD collapse           -> refuted/ood-failure
         b. does not beat verbal   -> refuted/no-margin-over-verbalized
         c. else                   -> confirmed-shaped
      2. Else (no continuous fidelity):
         a. binarized signal clears its bar -> refuted/binary-only
         b. else                            -> refuted/no-signal
    """
    if has_continuous_fidelity(inputs, thresholds):
        if inputs.r2_ood < thresholds.r2_ood_min:
            return Verdict.REFUTED_OOD_FAILURE
        if inputs.probe_vs_vc_ci_low <= thresholds.vc_ci_floor:
            return Verdict.REFUTED_NO_MARGIN_OVER_VERBALIZED
        return Verdict.CONFIRMED_SHAPED

    if inputs.auc_binary >= thresholds.auc_binary_min:
        return Verdict.REFUTED_BINARY_ONLY
    return Verdict.REFUTED_NO_SIGNAL
