"""compare.py — AUROC and paired-bootstrap CI on hand-computed / planted cases (e3-0003).

- Perfect separation -> AUROC = 1.0; reversed -> 0.0; a seeded random score ~ 0.5.
- The paired bootstrap CI covers a known planted AUROC difference and excludes zero when the arms
  differ strongly, and includes zero when the two arms are identical.
- n_boot and ci_level are recorded on the result (they are pre-registered parameters, e3-0003/0004).
"""

from __future__ import annotations

import numpy as np
import pytest

from e3_validation.compare import auroc, paired_bootstrap_auroc_diff


def test_auroc_perfect_separation_is_one():
    labels = np.array([0, 0, 0, 1, 1, 1])
    scores = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])  # every positive scores above every negative
    assert auroc(scores, labels) == 1.0


def test_auroc_reversed_is_zero():
    labels = np.array([0, 0, 0, 1, 1, 1])
    scores = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])  # perfectly wrong ordering
    assert auroc(scores, labels) == 0.0


def test_auroc_random_is_near_half():
    rng = np.random.default_rng(0)
    n = 4000
    labels = rng.integers(0, 2, n)
    scores = rng.standard_normal(n)  # independent of labels
    assert abs(auroc(scores, labels) - 0.5) < 0.03


def test_auroc_fails_closed_on_single_class():
    with pytest.raises(ValueError):
        auroc(np.array([0.1, 0.2, 0.3]), np.array([1, 1, 1]))


def test_paired_bootstrap_covers_large_planted_difference_and_excludes_zero():
    # arm A separates the label strongly, arm B is random -> planted positive difference ~0.4.
    rng = np.random.default_rng(11)
    n = 400
    labels = rng.integers(0, 2, n)
    strong = labels + rng.normal(0.0, 0.5, n)
    weak = rng.standard_normal(n)
    res = paired_bootstrap_auroc_diff(strong, weak, labels, n_boot=2000, ci_level=0.95, seed=5)
    assert res.diff > 0.3
    assert res.ci_low <= res.diff <= res.ci_high  # the CI covers the observed difference
    assert res.excludes_zero and res.ci_low > 0.0  # large difference -> CI strictly above zero
    assert res.n_boot == 2000 and res.ci_level == 0.95  # pre-registered params recorded


def test_paired_bootstrap_identical_arms_includes_zero():
    rng = np.random.default_rng(12)
    n = 400
    labels = rng.integers(0, 2, n)
    scores = labels + rng.normal(0.0, 0.8, n)
    res = paired_bootstrap_auroc_diff(scores, scores, labels, n_boot=2000, ci_level=0.95, seed=5)
    assert res.diff == 0.0
    assert not res.excludes_zero  # identical arms -> the CI must include zero
    assert res.ci_low <= 0.0 <= res.ci_high
