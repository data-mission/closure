"""Fixture E — the family-band shortcut, re-read under the redesigned OOD metric.

Planted answer (by construction, see `_fixtures.make_ood_shortcut`): a family-specific indicator
coordinate carries each family's (large-variance) MEAN, dominating a weak but genuine within-family
signal ``0.3*(x_sig . w)``. Under a random same-family split the probe learns the indicator->mean map
and in-distribution R^2 is ~1. Under leave-one-family-out the held-out family's indicator is
constant-zero in training, so the probe cannot recover that family's LEVEL and the pooled-R^2 OOD
number collapses far below zero.

This is exactly the confound the redesign targets. The OLD OOD metric (pooled R^2) refuted this
fixture because the between-family LEVEL did not transfer — but the level is precisely the family-band
structure the audit ruled a confound. The NEW OOD metric scores the rank correlation WITHIN each
held-out family, where the genuine ``0.3*(x_sig . w)`` signal (shared across families, high
within-family SNR) DOES transfer. So this fixture now demonstrates the metric change itself: pooled
R^2 collapses while within-family Spearman transfers. The genuine OOD FAILURE case — a within-family
signal that does not transfer — is `make_family_specific_signal`, tested in `test_ood.py`.

Contract change from the pre-redesign suite (documented in VALIDATION.md): this fixture no longer
routes refuted/ood-failure, because the redesigned OOD gate is within-family Spearman, not pooled R^2.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import r2_score

from e3_validation.ood import leave_one_family_out_spearman
from e3_validation.probe import class_mean_predictor_r2, ridge_probe
from e3_validation.splits import in_distribution_split, leave_one_family_out

from ._fixtures import PASSING_THRESHOLDS, make_ood_shortcut, sign_class


def _indist(X, y):
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    cls = sign_class(y)
    r2_cm = class_mean_predictor_r2(y[train_idx], y[test_idx], cls[train_idx], cls[test_idx])
    return res, r2_cm


def _pooled_ood_r2(X, y, fam):
    y_true, y_pred = [], []
    for _f, train_idx, test_idx in leave_one_family_out(fam):
        res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
        y_true.append(y[test_idx])
        y_pred.append(res.predictions)
    return float(r2_score(np.concatenate(y_true), np.concatenate(y_pred)))


def test_indistribution_fidelity_is_high():
    X, y, _fam = make_ood_shortcut()
    res, r2_cm = _indist(X, y)
    assert res.r2 > 0.90  # the shortcut works when the family was seen in training
    assert res.r2 - r2_cm > PASSING_THRESHOLDS.r2_margin_over_classmean_min


def test_pooled_ood_r2_collapses_the_superseded_metric():
    # The OLD OOD metric collapses because the between-family LEVEL does not transfer...
    X, y, fam = make_ood_shortcut()
    assert _pooled_ood_r2(X, y, fam) < 0.0


def test_within_family_ood_spearman_transfers_the_new_metric():
    # ...but the genuine within-family signal DOES transfer: the redesigned OOD metric (within-held-
    # out-family Spearman, pooled mean over rotations) clears its bar, so the family-band collapse is
    # correctly NOT counted as a failure of within-family transfer.
    X, y, fam = make_ood_shortcut()
    ood = leave_one_family_out_spearman(X, y, fam)
    assert ood.pooled_spearman >= PASSING_THRESHOLDS.ood_pooled_spearman_min
    assert ood.min_rotation_spearman >= PASSING_THRESHOLDS.ood_per_family_floor
