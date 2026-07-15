"""Fixture A — a genuine linear signal that transfers OOD -> verdict confirmed-shaped.

Planted answer (by construction, see `_fixtures.make_linear_signal`): the ridge probe recovers the
shared signal direction, so R^2 and Spearman are near 1 both in-distribution and under
leave-one-family-out, and the continuous probe materially exceeds the class-mean predictor. Paired
with a probe correctness arm that beats a weak verbalized-confidence arm, the pre-registered verdict
must land on confirmed-shaped.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import r2_score

from e3_validation.compare import paired_bootstrap_auroc_diff
from e3_validation.fidelity import (
    continuous_fidelity,
    family_mean_oracle_r2,
    within_family_metrics,
)
from e3_validation.ood import leave_one_family_out_spearman
from e3_validation.probe import class_mean_predictor_r2, ridge_probe
from e3_validation.splits import in_distribution_split, leave_one_family_out
from e3_validation.verdict import Verdict, decide

from ._fixtures import (
    PASSING_THRESHOLDS,
    make_linear_signal,
    make_verbalized_confidence_arms,
    passing_inputs,
    sign_class,
)


def _pooled_ood_r2(X, y, fam):
    """Leave-one-family-out, pooled: concatenate every held-out family's predictions and score one
    R^2. Pooling (not averaging per-family R^2) is robust to a single family whose mean happens to
    match the global mean."""
    y_true, y_pred = [], []
    for _f, train_idx, test_idx in leave_one_family_out(fam):
        res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
        y_true.append(y[test_idx])
        y_pred.append(res.predictions)
    return float(r2_score(np.concatenate(y_true), np.concatenate(y_pred)))


def test_indistribution_fidelity_is_high():
    X, y, _fam = make_linear_signal()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    assert res.r2 > 0.95
    assert res.spearman > 0.95


def test_ood_transfers():
    X, y, fam = make_linear_signal()
    assert _pooled_ood_r2(X, y, fam) > 0.95  # signal identical across families -> transfers


def test_continuous_probe_beats_class_mean_predictor():
    X, y, _fam = make_linear_signal()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    cls = sign_class(y)
    r2_cm = class_mean_predictor_r2(y[train_idx], y[test_idx], cls[train_idx], cls[test_idx])
    # the continuous read explains substantially more than the class alone
    assert res.r2 - r2_cm > 0.10


def test_probe_beats_verbalized_confidence():
    probe_scores, vc_scores, correctness = make_verbalized_confidence_arms()
    result = paired_bootstrap_auroc_diff(
        probe_scores, vc_scores, correctness, n_boot=2000, ci_level=0.95, seed=3
    )
    assert result.diff > 0.0
    assert result.excludes_zero  # CI strictly above zero -> probe beats verbalized confidence
    assert result.ci_low > 0.0


def test_within_family_signal_transfers_ood():
    # the redesigned OOD metric: within-held-out-family Spearman, pooled = mean over rotations.
    X, y, fam = make_linear_signal()
    ood = leave_one_family_out_spearman(X, y, fam)
    assert ood.pooled_spearman > 0.95  # the shared signal transfers within every held-out family
    assert ood.min_rotation_spearman > 0.95
    assert not ood.any_range_uncovered  # homogeneous family means -> ranges cover each other


def test_verdict_is_confirmed_shaped():
    # end-to-end integration through the redesigned instrument: two-part fidelity, within-family
    # fidelity, family-oracle margin, within-family OOD Spearman, and beats-verbalized.
    X, y, fam = make_linear_signal()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])

    nondeg = np.ones(len(test_idx), dtype=bool)  # this fixture has no degenerate-floor items
    r2_nd, sp_nd, n_nd = continuous_fidelity(res.predictions, y[test_idx], nondeg)
    wf_r2, wf_sp = within_family_metrics(
        res.predictions, y[test_idx], y[train_idx], fam[test_idx], fam[train_idx]
    )
    fam_oracle = family_mean_oracle_r2(y[train_idx], y[test_idx], fam[train_idx], fam[test_idx])
    ood = leave_one_family_out_spearman(X, y, fam)

    cls = sign_class(y)
    r2_cm = class_mean_predictor_r2(y[train_idx], y[test_idx], cls[train_idx], cls[test_idx])

    probe_scores, vc_scores, correctness = make_verbalized_confidence_arms()
    vc = paired_bootstrap_auroc_diff(
        probe_scores, vc_scores, correctness, n_boot=2000, ci_level=0.95, seed=3
    )

    inputs = passing_inputs(
        r2_nondegenerate=r2_nd,
        spearman_nondegenerate=sp_nd,
        n_nondegenerate=n_nd,
        n_degenerate=0,
        within_family_spearman=wf_sp,
        within_family_r2=wf_r2,
        within_family_spearman_length_resid=wf_sp,  # no length variable in this fixture
        family_oracle_r2=fam_oracle,
        family_oracle_margin=res.r2 - fam_oracle,
        r2_indist=res.r2,
        r2_classmean_indist=r2_cm,  # retained B2 reporting
        ood_pooled_spearman=ood.pooled_spearman,
        ood_min_rotation_spearman=ood.min_rotation_spearman,
        ood_range_uncovered=ood.any_range_uncovered,
        probe_vs_vc_ci_low=vc.ci_low,
    )
    assert decide(inputs, PASSING_THRESHOLDS) is Verdict.CONFIRMED_SHAPED
