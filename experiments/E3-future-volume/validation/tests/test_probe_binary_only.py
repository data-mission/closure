"""Fixture C — the discriminating case: x encodes only the class of y -> refuted/binary-only.

Planted answer (by construction, see `_fixtures.make_binary_only`): x carries the class c = sign(y)
but nothing about the within-class magnitude of y. So the SEP-style logistic median-split probe
reads the class with high AUROC, while the continuous ridge R^2 does NOT materially exceed the
oracle class-mean predictor — the probe read only the binarized class SEP already established. The
pre-registered verdict must land on refuted/binary-only, NOT confirmed-shaped. This is the branch
that stops "volume of reachable futures" from being decoration over an existing binary result.
"""

from __future__ import annotations

from e3_validation.probe import class_mean_predictor_r2, logistic_median_split_probe, ridge_probe
from e3_validation.splits import in_distribution_split
from e3_validation.verdict import Verdict, VerdictInputs, decide, has_continuous_fidelity

from ._fixtures import PASSING_THRESHOLDS, make_binary_only, sign_class


def _fit():
    X, y, _c = make_binary_only()
    train_idx, test_idx = in_distribution_split(len(y), test_fraction=0.25, seed=1)
    reg = ridge_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    binr = logistic_median_split_probe(X[train_idx], y[train_idx], X[test_idx], y[test_idx])
    cls = sign_class(y)
    r2_cm = class_mean_predictor_r2(y[train_idx], y[test_idx], cls[train_idx], cls[test_idx])
    return reg, binr, r2_cm


def test_binarized_auroc_is_high():
    _reg, binr, _cm = _fit()
    assert binr.auroc > 0.90  # the class is readable from x


def test_continuous_probe_does_not_exceed_class_mean():
    reg, _binr, r2_cm = _fit()
    # everything x says about y is the class; the continuous read adds no material margin.
    assert (reg.r2 - r2_cm) < PASSING_THRESHOLDS.r2_margin_over_classmean_min


def test_no_continuous_fidelity_despite_positive_r2():
    reg, _binr, r2_cm = _fit()
    inputs = VerdictInputs(
        r2_indist=reg.r2,
        r2_classmean_indist=r2_cm,
        r2_ood=reg.r2,
        auc_binary=0.99,
        probe_vs_vc_ci_low=1.0,
    )
    # R^2 alone can clear the fidelity bar, but the class-mean margin clause denies fidelity.
    assert not has_continuous_fidelity(inputs, PASSING_THRESHOLDS)


def test_verdict_is_binary_only():
    reg, binr, r2_cm = _fit()
    inputs = VerdictInputs(
        r2_indist=reg.r2,
        r2_classmean_indist=r2_cm,
        r2_ood=reg.r2,
        auc_binary=binr.auroc,
        probe_vs_vc_ci_low=1.0,  # even a "beats VC" arm cannot rescue a binary-only signal
    )
    assert decide(inputs, PASSING_THRESHOLDS) is Verdict.REFUTED_BINARY_ONLY
