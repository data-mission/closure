"""E8 break-test fixtures (0008 (iii) break definition).

Exact one-sample binomial crossing matches the analytic upper tail and its critical count;
the three-conjunct monotonicity gate passes a true dose-response and FAILS the flat-then-jump
and noisy-dip curves the break definition forbids; Bonferroni alpha divides over the axis count.

Every expected value is hand-computed or recomputed independently of the implementation (the
convention in tests/test_stats.py). Each oracle carries a comment naming what it protects.
"""

from __future__ import annotations

import math

from scipy import stats as sp

from closure_harness.stats import (
    bonferroni_alpha,
    exact_binomial_crossing,
    monotonicity_gate,
)

ALPHA = 0.05
AC3 = ALPHA / 3  # m=3 axes Bonferroni level, the standard scenario


# ---------------------------------------------------------------------------
# exact_binomial_crossing — the top-level crossing test (F1)
# ---------------------------------------------------------------------------

def test_o1_exact_upper_tail_matches_hand_sum():
    # O1 (protects: the exact tail is the binomial survival, not a normal approx).
    # n=20, theta=0.10, observe k=5. Hand: 1 - sum_{i<=4} C(20,i) 0.1^i 0.9^(20-i).
    hand = 1.0 - sum(math.comb(20, i) * 0.10**i * 0.90 ** (20 - i) for i in range(0, 5))
    r = exact_binomial_crossing(5, 20, 0.10, AC3)
    assert math.isclose(r.p_value, hand, rel_tol=1e-12)  # hand == 0.0431745, the memo O1 value


def test_o2_critical_count_at_theta5_n60():
    # O2 (protects: the discrete critical count k*, not a smooth boundary).
    # n=60, theta=0.05, alpha/3: smallest k with P(K>=k)<=0.0167. Hand-checked k*=8.
    r = exact_binomial_crossing(8, 60, 0.05, AC3)
    assert r.critical_count == 8
    assert r.crossed is True
    # tail at k*=8 is <= alpha_corr, tail at k*-1=7 is strictly greater (k* is the SMALLEST).
    assert float(sp.binom.sf(7, 60, 0.05)) <= AC3
    assert float(sp.binom.sf(6, 60, 0.05)) > AC3


def test_o2b_critical_count_at_theta5_n150():
    # O2b (protects: the frozen recommendation cell k*=15 at N=150, theta=5%, m=3).
    r = exact_binomial_crossing(15, 150, 0.05, AC3)
    assert r.critical_count == 15
    assert math.isclose(float(sp.binom.sf(14, 150, 0.05)), 0.008476, rel_tol=1e-4)  # memo 0.00848
    assert float(sp.binom.sf(14, 150, 0.05)) <= AC3
    assert float(sp.binom.sf(13, 150, 0.05)) > AC3


def test_crossing_below_threshold_does_not_fire():
    # Protects: a count that does not reach k* reports crossed=False (no false crossing).
    r = exact_binomial_crossing(14, 150, 0.05, AC3)  # one below k*=15
    assert r.crossed is False


def test_crossing_unreachable_threshold_returns_none():
    # Protects: a threshold so high that no k in [0,n] can reach alpha -> critical None, no crossing.
    r = exact_binomial_crossing(3, 3, 0.90, AC3)  # n=3, theta=0.90: P(K>=3)=0.729 > alpha
    assert r.critical_count is None
    assert r.crossed is False


# ---------------------------------------------------------------------------
# monotonicity_gate — three-conjunct gate, conjuncts (a) CA Z>0 and (b) strict rise (F2)
# ---------------------------------------------------------------------------

def test_o3_gate_pass_true_dose_response():
    # O3 (protects: a genuine rising dose-response passes both conjuncts).
    # counts 2/5/9 of 60: rates 3.33% < 8.33% < 15%, CA Z = +2.2454.
    r = monotonicity_gate([2, 5, 9], [60, 60, 60])
    assert math.isclose(r.z, 2.2454, rel_tol=1e-3)
    assert r.ca_uptrend is True
    assert r.strict_rise is True
    assert r.gate_pass is True


def test_o4_gate_fail_downtrend():
    # O4 (protects: a downtrend fails; O3/O4 reversal symmetry is the sign-correctness check).
    # counts 9/5/2 of 60: CA Z = -2.2454, rates strictly DECREASE.
    r = monotonicity_gate([9, 5, 2], [60, 60, 60])
    assert math.isclose(r.z, -2.2454, rel_tol=1e-3)
    assert r.ca_uptrend is False
    assert r.strict_rise is False
    assert r.gate_pass is False


def test_o5_gate_fail_flat_then_jump():
    # O5 (LOAD-BEARING: the flat-then-jump curve 0008 (iii) forbids. CA Z is LARGE POSITIVE,
    # so conjunct (a) alone would wrongly pass it; conjunct (b) strict-rise is what kills it).
    # counts 0/0/18 of 150: rates 0% / 0% / 12%, CA Z = +5.303.
    r = monotonicity_gate([0, 0, 18], [150, 150, 150])
    assert r.z > 5.0                       # NOT small — the whole point of O5
    assert math.isclose(r.z, 5.303, rel_tol=1e-3)
    assert r.ca_uptrend is True            # (a) passes
    assert r.strict_rise is False          # (b) fails on the flat first pair (0 < 0 is false)
    assert r.gate_pass is False            # gate correctly rejects the single bump


def test_o6_gate_fail_flat():
    # O6 (protects: a fully flat curve is not a trend). counts 4/4/4 of 60: Z=0, no strict rise.
    r = monotonicity_gate([4, 4, 4], [60, 60, 60])
    assert r.z == 0.0
    assert r.ca_uptrend is False
    assert r.strict_rise is False
    assert r.gate_pass is False


def test_o7_gate_fail_noise_breaks_true_trend():
    # O7 (protects/documents the ACCEPTED COST: a true-rising curve can fail (b) under noise).
    # counts 5/4/24 of 150: rates 3.33% / 2.67% / 16%, CA Z = +4.208 but the first pair dips.
    r = monotonicity_gate([5, 4, 24], [150, 150, 150])
    assert r.z > 0.0
    assert math.isclose(r.z, 4.208, rel_tol=1e-3)
    assert r.ca_uptrend is True
    assert r.strict_rise is False          # 3.33% -> 2.67% dip: conservative failure by design
    assert r.gate_pass is False


def test_gate_rejects_fewer_than_three_levels():
    # Protects: 0008 (iii) requires >= 3 dose levels; two levels is not a dose-response.
    try:
        monotonicity_gate([1, 5], [60, 60])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for < 3 levels")


# ---------------------------------------------------------------------------
# monotonicity_gate + exact_binomial_crossing on the PERSIST side (side-agnostic reuse, §7.6)
# ---------------------------------------------------------------------------

def test_op1_persist_critical_count_theta10_n150():
    # OP1 (protects: persist-side crossing reuses F1 verbatim; theta_persist=10%, N=150, m=3).
    r = exact_binomial_crossing(24, 150, 0.10, AC3)
    assert r.critical_count == 24
    assert math.isclose(float(sp.binom.sf(23, 150, 0.10)), 0.01431, rel_tol=1e-3)
    assert float(sp.binom.sf(23, 150, 0.10)) <= AC3
    assert float(sp.binom.sf(22, 150, 0.10)) > AC3   # tail at k*-1 = 0.02564 > alpha_corr


def test_op2_persist_power_cell():
    # OP2 (protects: the §7.4 table cell — power @ true 18%, N=150, theta=10%, m=3 = 0.768).
    # power = P(K >= k* | n, p_true); k*=24 from OP1.
    power = float(sp.binom.sf(24 - 1, 150, 0.18))
    assert math.isclose(power, 0.768, rel_tol=1e-2)


def test_op3_persist_floor_reconciliation():
    # OP3 (protects: the persist metric extractor's anchor — E5 Arm-B 7/120 = 1 - 0.9417).
    assert math.isclose(7 / 120, 0.058333, rel_tol=1e-4)
    assert math.isclose(1.0 - 7 / 120, 0.941667, rel_tol=1e-5)  # VERDICT completeness 0.9417


def test_op4_persist_power_n300_true15():
    # OP4 (protects: the recommendation number — N=300, theta=10%, true 15%, m=3 = 0.710).
    k = exact_binomial_crossing(0, 300, 0.10, AC3).critical_count  # k* only depends on n,theta,ac
    power = float(sp.binom.sf(k - 1, 300, 0.15))
    assert k == 42
    assert math.isclose(power, 0.710, rel_tol=1e-2)


def test_op5_persist_power_n300_true18():
    # OP5 (protects: the recommendation number — N=300, theta=10%, true 18%, m=3 = 0.973).
    k = exact_binomial_crossing(0, 300, 0.10, AC3).critical_count
    power = float(sp.binom.sf(k - 1, 300, 0.18))
    assert k == 42
    assert math.isclose(power, 0.973, rel_tol=1e-2)


# ---------------------------------------------------------------------------
# bonferroni_alpha — multiplicity over the final axis count (F3)
# ---------------------------------------------------------------------------

def test_bonferroni_alpha_m3_m4():
    # Protects: divide-alpha over axis count; m=3 -> 0.016667, m=4 -> 0.012500 (both used in §4).
    assert math.isclose(bonferroni_alpha(3), 0.05 / 3, rel_tol=1e-12)
    assert math.isclose(bonferroni_alpha(4), 0.05 / 4, rel_tol=1e-12)
    assert math.isclose(bonferroni_alpha(3), AC3, rel_tol=1e-12)


def test_bonferroni_alpha_rejects_nonpositive():
    try:
        bonferroni_alpha(0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for axis_count <= 0")
