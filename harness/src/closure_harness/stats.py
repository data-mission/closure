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
