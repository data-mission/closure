"""Determinism — every pipeline function run twice with the same seed yields identical output.

e3-0004 claims the purely algorithmic steps (the closed-form ridge fit on a fixed feature matrix and
the volume computation on fixed embeddings) are EXACTLY reproducible on fixed inputs, and that seeded
steps reproduce identically given the same seed. These assertions are bit-identical (``==`` /
``array_equal``), not approximate.
"""

from __future__ import annotations

import numpy as np

from e3_validation.compare import paired_bootstrap_auroc_diff
from e3_validation.probe import logistic_median_split_probe, ridge_probe, select_alpha
from e3_validation.splits import in_distribution_split
from e3_validation.volume import semantic_volume

from ._fixtures import make_binary_only, make_linear_signal, make_no_signal


def test_volume_is_bit_identical():
    X, _y, _f = make_linear_signal()
    assert semantic_volume(X[:10]) == semantic_volume(X[:10])


def test_ridge_probe_is_bit_identical():
    X, y, _f = make_linear_signal()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    a = ridge_probe(X[tr], y[tr], X[te], y[te])
    b = ridge_probe(X[tr], y[tr], X[te], y[te])
    assert a.alpha == b.alpha
    assert a.r2 == b.r2
    assert a.spearman == b.spearman
    assert np.array_equal(a.predictions, b.predictions)


def test_alpha_selection_is_bit_identical():
    X, y, _f = make_linear_signal()
    tr, _te = in_distribution_split(len(y), 0.25, seed=1)
    assert select_alpha(X[tr], y[tr]) == select_alpha(X[tr], y[tr])


def test_logistic_probe_is_bit_identical():
    X, y, _c = make_binary_only()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    a = logistic_median_split_probe(X[tr], y[tr], X[te], y[te])
    b = logistic_median_split_probe(X[tr], y[tr], X[te], y[te])
    assert a.threshold == b.threshold
    assert a.auroc == b.auroc


def test_split_is_bit_identical():
    a = in_distribution_split(240, 0.25, seed=1)
    b = in_distribution_split(240, 0.25, seed=1)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_paired_bootstrap_is_bit_identical():
    X, y = make_no_signal()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    # build two arms from the same data; the bootstrap seed fixes the resampling exactly.
    labels = (y[te] > np.median(y[tr])).astype(int)
    a_scores = X[te] @ np.ones(X.shape[1])
    b_scores = X[te] @ np.arange(X.shape[1])
    r1 = paired_bootstrap_auroc_diff(a_scores, b_scores, labels, n_boot=500, ci_level=0.95, seed=9)
    r2 = paired_bootstrap_auroc_diff(a_scores, b_scores, labels, n_boot=500, ci_level=0.95, seed=9)
    assert r1 == r2
