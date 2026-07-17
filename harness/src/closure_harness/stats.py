"""Comparison test (decision 0007).

- Pairwise two-proportion z-test on contamination rate, Bonferroni-corrected for 3 comparisons,
  alpha = 0.05.
- Minimum detectable effect (MDE) for N = 60.
- Completeness non-inferiority, paired, absolute margin delta = 0.10.

Contamination is a proportion (must-change conclusions still asserted, pooled over tasks), so
the arm-level test is a two-proportion z-test on (successes, trials) per arm. Completeness
non-inferiority is paired at the task level (same tasks scored under each arm).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from scipy import stats as _sp

from .config import CONFIG, StatsConfig


@dataclass(frozen=True)
class ZTestResult:
    p_hat_a: float
    p_hat_b: float
    z: float
    p_value: float
    p_value_corrected: float
    significant: bool


def two_proportion_ztest(
    successes_a: int,
    trials_a: int,
    successes_b: int,
    trials_b: int,
    config: StatsConfig = CONFIG.stats,
) -> ZTestResult:
    """Pooled two-proportion z-test, two-sided, Bonferroni-corrected for 3 comparisons.

    'significant' is judged against the corrected alpha (0007: three pairwise comparisons).
    """
    if trials_a <= 0 or trials_b <= 0:
        raise ValueError("both arms need trials > 0")
    p_a = successes_a / trials_a
    p_b = successes_b / trials_b
    pooled = (successes_a + successes_b) / (trials_a + trials_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / trials_a + 1 / trials_b))
    if se == 0.0:
        z = 0.0
        p_value = 1.0
    else:
        z = (p_a - p_b) / se
        p_value = 2.0 * _sp.norm.sf(abs(z))
    p_corrected = min(1.0, p_value * config.bonferroni_comparisons)
    return ZTestResult(
        p_hat_a=p_a,
        p_hat_b=p_b,
        z=z,
        p_value=p_value,
        p_value_corrected=p_corrected,
        significant=p_corrected < config.alpha,
    )


def minimum_detectable_effect(
    baseline_rate: float,
    n_per_arm: int = None,
    power: float = 0.8,
    config: StatsConfig = CONFIG.stats,
) -> float:
    """Smallest absolute rate difference detectable at N per arm, Bonferroni-corrected alpha.

    Two-sided, unpooled normal approximation around the baseline rate. Returns the effect
    size delta such that a two-proportion test has the requested power.
    """
    n = config.n_tasks if n_per_arm is None else n_per_arm
    alpha = config.alpha / config.bonferroni_comparisons
    z_alpha = _sp.norm.ppf(1 - alpha / 2.0)
    z_beta = _sp.norm.ppf(power)
    p = baseline_rate
    # Solve delta from: delta = (z_alpha + z_beta) * sqrt(2 p (1-p) / n)
    return (z_alpha + z_beta) * math.sqrt(2 * p * (1 - p) / n)


@dataclass(frozen=True)
class NonInferiorityResult:
    mean_c: float
    mean_b: float
    diff: float
    margin: float
    non_inferior: bool


def completeness_non_inferiority(
    completeness_c: Sequence[float],
    completeness_b: Sequence[float],
    config: StatsConfig = CONFIG.stats,
) -> NonInferiorityResult:
    """Paired non-inferiority of C's completeness vs B's, absolute margin delta = 0.10.

    Non-inferior iff mean(C) >= mean(B) - delta. At the exact boundary (C = B - delta) the
    verdict is non-inferior (>=), matching the pre-registered boundary case.
    """
    if len(completeness_c) != len(completeness_b):
        raise ValueError("paired completeness vectors must have equal length")
    mean_c = sum(completeness_c) / len(completeness_c)
    mean_b = sum(completeness_b) / len(completeness_b)
    delta = config.non_inferiority_delta
    return NonInferiorityResult(
        mean_c=mean_c,
        mean_b=mean_b,
        diff=mean_c - mean_b,
        margin=delta,
        non_inferior=mean_c >= mean_b - delta,
    )


# ---------------------------------------------------------------------------
# E8 break-test additions (decision 0008 Phase 0): exact one-sided binomial
# crossing of one dose level against a frozen absolute threshold, the
# three-conjunct monotonicity gate (CA trend + strict observed rise), and
# Bonferroni alpha over the final axis count. Parameter-agnostic in the outcome
# side: the same functions read the contamination (must_change) and persist
# (must_persist) breaks. Imports above already cover these (math, dataclass,
# Sequence, scipy _sp, CONFIG/StatsConfig).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BinomCrossingResult:
    p_hat: float
    critical_count: int | None
    p_value: float
    crossed: bool


def exact_binomial_crossing(
    count: int,
    trials: int,
    threshold: float,
    alpha_corrected: float,
) -> BinomCrossingResult:
    """One-sided exact-binomial crossing of one dose level against a fixed absolute threshold.

    H0: p <= threshold, H1: p > threshold. Reject (declare the crossing) iff the observed
    count reaches the smallest k* whose upper-tail probability under p=threshold is
    <= alpha_corrected. Exact (not normal-approx): the upper tail is scipy's binomial survival
    function, which is what keeps the small-N power honest (threshold-memo §4 cross-check).

    alpha_corrected is the Bonferroni-divided level (bonferroni_alpha below), passed in rather
    than read from config so the caller owns the axis count. p_value is the exact upper tail at
    the observed count. critical_count is None when even count==trials cannot reach the level
    (a threshold too high for this N to ever cross), in which case crossed is False.
    """
    if trials <= 0:
        raise ValueError("trials must be > 0")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    p_hat = count / trials
    critical = _critical_count(trials, threshold, alpha_corrected)
    # P(K >= count | trials, threshold) = survival at count-1.
    p_value = float(_sp.binom.sf(count - 1, trials, threshold))
    crossed = critical is not None and count >= critical
    return BinomCrossingResult(
        p_hat=p_hat,
        critical_count=critical,
        p_value=p_value,
        crossed=crossed,
    )


def _critical_count(trials: int, threshold: float, alpha_corrected: float) -> int | None:
    """Smallest k* with P(K >= k* | trials, threshold) <= alpha_corrected, or None if none."""
    for k in range(0, trials + 1):
        if float(_sp.binom.sf(k - 1, trials, threshold)) <= alpha_corrected:
            return k
    return None


@dataclass(frozen=True)
class MonotonicityResult:
    z: float
    p_value: float
    rates: tuple[float, ...]
    ca_uptrend: bool
    strict_rise: bool
    gate_pass: bool


def monotonicity_gate(
    counts: Sequence[int],
    trials: Sequence[int],
) -> MonotonicityResult:
    """Two of the three break conjuncts (0008 (iii) monotone dose-response), on ordered levels.

    Computes (a) the Cochran-Armitage trend Z across the >=3 ordered dose levels (integer dose
    scores 0..L-1, per-item binary response) and (b) the strict observed rise
    rate_0 < rate_1 < ... < rate_top. gate_pass is (a) AND (b). The third conjunct — the
    top-level crossing firing — is combined by the caller (it lives in exact_binomial_crossing),
    because the crossing consumes the axis's alpha and this gate does not.

    Conjunct (b) is what excludes a flat-then-jump curve: a top-only jump has a large positive
    CA Z (a 0/0/high curve gives Z well above 0), so (a) alone would wrongly pass the single-bump
    curve 0008 (iii) forbids. (b) is tolerance-free (pure observed ordering) and can only fail
    under sampling noise — the conservative, anti-fishing direction. rates are returned so a
    noise-failed (b) is visible as such (threshold-memo §2ii).
    """
    if len(counts) != len(trials):
        raise ValueError("counts and trials must have equal length")
    if len(counts) < 3:
        raise ValueError("monotone dose-response requires >= 3 levels (0008 (iii))")
    if any(n <= 0 for n in trials):
        raise ValueError("every dose level needs trials > 0")

    rates = tuple(counts[i] / trials[i] for i in range(len(counts)))
    z = _cochran_armitage_z(counts, trials)
    ca_uptrend = z > 0.0
    strict_rise = all(rates[i] < rates[i + 1] for i in range(len(rates) - 1))
    return MonotonicityResult(
        z=z,
        p_value=float(_sp.norm.sf(z)),
        rates=rates,
        ca_uptrend=ca_uptrend,
        strict_rise=strict_rise,
        gate_pass=ca_uptrend and strict_rise,
    )


def _cochran_armitage_z(counts: Sequence[int], trials: Sequence[int]) -> float:
    """Cochran-Armitage trend Z with integer dose scores 0..L-1.

    Z = sum_i s_i (k_i - n_i p_bar) / sqrt( p_bar (1 - p_bar) sum_i n_i (s_i - s_bar)^2 ),
    p_bar = sum k / sum n, s_bar = sum s_i n_i / sum n. Returns 0.0 when the variance term is
    0 (a fully-flat or degenerate table), matching the se==0 -> z=0 convention in
    two_proportion_ztest (stats.py:51).
    """
    scores = range(len(counts))
    total_n = sum(trials)
    p_bar = sum(counts) / total_n
    s_bar = sum(s * trials[s] for s in scores) / total_n
    numerator = sum(s * (counts[s] - trials[s] * p_bar) for s in scores)
    variance = p_bar * (1.0 - p_bar) * sum(trials[s] * (s - s_bar) ** 2 for s in scores)
    if variance <= 0.0:
        return 0.0
    return numerator / math.sqrt(variance)


def bonferroni_alpha(axis_count: int, config: StatsConfig = CONFIG.stats) -> float:
    """Bonferroni-divided alpha over the final frozen axis count (0008 (iv) multiplicity).

    Each axis contributes exactly one verdict-bearing crossing test (whichever outcome side
    carries that axis's registered break), so the family size is the axis count. Divide-alpha
    form (mirrors minimum_detectable_effect at stats.py:80) so the crossing p-values are reported
    uncorrected and compared against this returned level.
    """
    if axis_count <= 0:
        raise ValueError("axis_count must be > 0")
    return config.alpha / axis_count
