"""ood.py — leave-one-family-out within-held-out-family Spearman, pooling, range coverage (redesign D).

Planted answers:
  * make_linear_signal — a shared within-family signal transfers to every held-out family (pooled and
    every rotation clear their bars), ranges covered;
  * make_family_specific_signal — genuine within-family signal that lives in a family-specific block
    does NOT transfer: the held-out family's block was never trained, so its within-family Spearman
    collapses -> REFUTED_OOD_FAILURE, and because all families share the same volume range it is a
    collapse, not an uncovered-range extrapolation;
  * make_family_band_only — no within-family signal at all, so OOD within-family Spearman is ~0;
  * range coverage flags a genuinely out-of-range held-out family and pooling is the mean over
    rotations.
"""

from __future__ import annotations

import numpy as np

from e3_validation.fidelity import within_family_metrics
from e3_validation.ood import leave_one_family_out_spearman, range_uncovered
from e3_validation.probe import ridge_probe
from e3_validation.splits import in_distribution_split
from e3_validation.verdict import Verdict, decide

from ._fixtures import PASSING_THRESHOLDS as T
from ._fixtures import (
    make_family_band_only,
    make_family_specific_signal,
    make_linear_signal,
    passing_inputs,
)


def test_shared_signal_transfers():
    X, y, fam = make_linear_signal()
    ood = leave_one_family_out_spearman(X, y, fam)
    assert ood.pooled_spearman > 0.95
    assert ood.min_rotation_spearman > 0.95
    assert not ood.any_range_uncovered


def test_family_specific_signal_does_not_transfer():
    X, y, fam = make_family_specific_signal()
    ood = leave_one_family_out_spearman(X, y, fam)
    # in-distribution the block signal is learnable (checked below), but it does not transfer OOD.
    assert ood.pooled_spearman < T.ood_pooled_spearman_min
    assert ood.min_rotation_spearman < T.ood_per_family_floor
    assert not ood.any_range_uncovered  # same volume range across families -> collapse, not extrapolation


def test_family_specific_signal_is_learnable_in_distribution():
    # confirms the OOD failure above is a transfer failure, not an absence of signal.
    X, y, _fam = make_family_specific_signal()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    res = ridge_probe(X[tr], y[tr], X[te], y[te])
    assert res.r2 > 0.50  # every family's block coefficient is learnable when the family is in train


def test_family_band_only_has_no_within_family_transfer():
    X, y, fam = make_family_band_only()
    ood = leave_one_family_out_spearman(X, y, fam)
    assert ood.pooled_spearman < T.ood_pooled_spearman_min


def test_pooled_is_mean_over_rotations():
    X, y, fam = make_linear_signal()
    ood = leave_one_family_out_spearman(X, y, fam)
    per = np.array([r.spearman for r in ood.per_rotation])
    assert np.isclose(ood.pooled_spearman, per.mean())
    assert np.isclose(ood.min_rotation_spearman, per.min())


def test_range_uncovered_flags_extrapolation_not_tail_noise():
    train = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    # a hair past the max -> covered (finite-sample tail); a whole band past -> uncovered.
    assert not range_uncovered(np.array([1.0, 5.1]), train)
    assert range_uncovered(np.array([1.0, 9.0]), train)
    assert range_uncovered(np.array([-4.0, 2.0]), train)


def test_verdict_is_ood_failure_for_family_specific_signal():
    # end-to-end: in-distribution fidelity present, OOD within-family Spearman collapses.
    X, y, fam = make_family_specific_signal()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    res = ridge_probe(X[tr], y[tr], X[te], y[te])
    _wf_r2, wf_sp = within_family_metrics(res.predictions, y[te], y[tr], fam[te], fam[tr])
    ood = leave_one_family_out_spearman(X, y, fam)
    inputs = passing_inputs(
        r2_nondegenerate=res.r2,
        spearman_nondegenerate=res.spearman,
        within_family_spearman=wf_sp,
        within_family_spearman_length_resid=wf_sp,
        family_oracle_margin=0.30,  # in-distribution the probe beats the family-mean oracle
        ood_pooled_spearman=ood.pooled_spearman,
        ood_min_rotation_spearman=ood.min_rotation_spearman,
        ood_range_uncovered=ood.any_range_uncovered,
    )
    assert decide(inputs, T) is Verdict.REFUTED_OOD_FAILURE
