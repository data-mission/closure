"""Stats fixtures (0007 comparison test).

Two-proportion z-test significance matches scipy analytic expectation; non-inferiority verdicts
are correct at the exact pre-registered boundary (C = B - delta); MDE for N = 60 is the analytic
value.
"""

from __future__ import annotations

import math

from scipy import stats as sp

from closure_harness.config import CONFIG
from closure_harness.stats import (
    completeness_non_inferiority,
    minimum_detectable_effect,
    two_proportion_ztest,
)


def _analytic_z(sa, na, sb, nb):
    pa, pb = sa / na, sb / nb
    pooled = (sa + sb) / (na + nb)
    se = math.sqrt(pooled * (1 - pooled) * (1 / na + 1 / nb))
    z = (pa - pb) / se
    return z, 2.0 * sp.norm.sf(abs(z))


def test_ztest_matches_scipy_analytic():
    # Strongly separated proportions: 10/60 vs 40/60.
    r = two_proportion_ztest(10, 60, 40, 60)
    z, p = _analytic_z(10, 60, 40, 60)
    assert math.isclose(r.z, z, rel_tol=1e-12)
    assert math.isclose(r.p_value, p, rel_tol=1e-12)
    assert math.isclose(r.p_value_corrected, min(1.0, p * 3), rel_tol=1e-12)
    assert bool(r.significant) is True


def test_ztest_null_not_significant():
    # Equal proportions -> z 0, p 1, not significant.
    r = two_proportion_ztest(30, 60, 30, 60)
    assert r.z == 0.0
    assert r.p_value == 1.0
    assert bool(r.significant) is False


def test_ztest_bonferroni_flips_verdict():
    # 16/60 vs 28/60: p = 0.023 (< alpha uncorrected) but corrected 0.069 (>= alpha).
    r = two_proportion_ztest(16, 60, 28, 60)
    assert r.p_value < CONFIG.stats.alpha
    assert r.p_value_corrected >= CONFIG.stats.alpha
    assert math.isclose(r.p_value_corrected, min(1.0, r.p_value * 3), rel_tol=1e-12)
    # verdict uses the corrected value: significant uncorrected, NOT significant corrected.
    assert bool(r.significant) is False


def test_mde_matches_closed_form():
    baseline = 0.5
    alpha = CONFIG.stats.alpha / CONFIG.stats.bonferroni_comparisons
    z_alpha = sp.norm.ppf(1 - alpha / 2)
    z_beta = sp.norm.ppf(0.8)
    expected = (z_alpha + z_beta) * math.sqrt(2 * baseline * (1 - baseline) / 60)
    assert math.isclose(minimum_detectable_effect(baseline), expected, rel_tol=1e-12)


def test_non_inferiority_boundary_is_non_inferior():
    # C exactly at B - delta must count as non-inferior (>=).
    delta = CONFIG.stats.non_inferiority_delta
    b = [0.80, 0.80, 0.80, 0.80]
    c = [x - delta for x in b]  # C = B - delta exactly
    r = completeness_non_inferiority(c, b)
    assert math.isclose(r.mean_c, r.mean_b - delta, abs_tol=1e-12)
    assert r.non_inferior is True


def test_non_inferiority_just_below_boundary_fails():
    delta = CONFIG.stats.non_inferiority_delta
    b = [0.80, 0.80, 0.80, 0.80]
    c = [x - delta - 0.01 for x in b]  # just worse than the margin
    r = completeness_non_inferiority(c, b)
    assert r.non_inferior is False


def test_non_inferiority_c_better_passes():
    r = completeness_non_inferiority([0.9, 0.9], [0.7, 0.7])
    assert r.non_inferior is True
