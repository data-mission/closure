"""Fixture B — negative control: y independent of x -> verdict refuted/no-signal.

Planted answer (by construction, see `_fixtures.make_no_signal`): there is no map from x to y, so
the pipeline MUST NOT manufacture signal. Held-out R^2 is ~0 (bounded below a small tolerance) and
the binarized median-split AUROC is ~0.5. The pre-registered verdict must land on refuted/no-signal.
"""

from __future__ import annotations

from e3_validation.probe import logistic_median_split_probe, ridge_probe
from e3_validation.splits import in_distribution_split
from e3_validation.verdict import Verdict, VerdictInputs, decide

from ._fixtures import PASSING_THRESHOLDS, make_no_signal


def test_regression_r2_is_near_zero():
    X, y = make_no_signal()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    res = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    # no signal to find: held-out R^2 must not be manufactured positive.
    assert res.r2 < 0.10


def test_binarized_auroc_is_near_chance():
    X, y = make_no_signal()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    res = logistic_median_split_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    assert res.auroc < PASSING_THRESHOLDS.auc_binary_min  # below the "binary signal exists" bar


def test_verdict_is_no_signal():
    X, y = make_no_signal()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    reg = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    binr = logistic_median_split_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    inputs = VerdictInputs(
        r2_indist=reg.r2,
        r2_classmean_indist=0.0,  # no class structure either
        r2_ood=reg.r2,
        auc_binary=binr.auroc,
        probe_vs_vc_ci_low=-1.0,  # irrelevant: no fidelity, so the branch never reaches VC
    )
    assert decide(inputs, PASSING_THRESHOLDS) is Verdict.REFUTED_NO_SIGNAL
