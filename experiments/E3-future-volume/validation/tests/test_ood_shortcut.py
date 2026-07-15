"""Fixture E — the OOD shortcut trap: in-dist fidelity, OOD collapse -> refuted/ood-failure.

Planted answer (by construction, see `_fixtures.make_ood_shortcut`): a family-specific indicator
coordinate carries each family's (large-variance) mean, dominating the weak true signal, so ridge
provably prefers the shortcut in-distribution and R^2 is ~1 on a random same-family split. Under
leave-one-family-out the held-out family's indicator is constant-zero in training, so its
coefficient is inert and the probe cannot recover that family's mean -> pooled OOD R^2 collapses far
below zero. This proves the OOD regime catches a shortcut probe an in-distribution-only evaluation
would have called a success. The pre-registered verdict must land on refuted/ood-failure.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import r2_score

from e3_validation.probe import class_mean_predictor_r2, ridge_probe
from e3_validation.splits import in_distribution_split, leave_one_family_out
from e3_validation.verdict import Verdict, VerdictInputs, decide

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


def test_ood_collapses():
    X, y, fam = make_ood_shortcut()
    r2_ood = _pooled_ood_r2(X, y, fam)
    assert r2_ood < 0.0  # held-out family's shortcut coordinate is unseen -> prediction collapses


def test_verdict_is_ood_failure():
    X, y, fam = make_ood_shortcut()
    res, r2_cm = _indist(X, y)
    r2_ood = _pooled_ood_r2(X, y, fam)
    inputs = VerdictInputs(
        r2_indist=res.r2,
        r2_classmean_indist=r2_cm,
        r2_ood=r2_ood,
        auc_binary=0.99,
        probe_vs_vc_ci_low=1.0,  # even a passing VC margin cannot rescue an OOD collapse
    )
    assert decide(inputs, PASSING_THRESHOLDS) is Verdict.REFUTED_OOD_FAILURE
