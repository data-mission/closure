"""Correctness-prediction comparison: AUROC and the paired bootstrap (e3-0003).

Every comparator and the E3 probe are scored as **correctness predictors** by AUROC over the
answerable subset, so the metric is identical across arms regardless of native output scale.
Pairwise differences (probe vs a baseline) are reported with **paired bootstrap confidence
intervals over prompts** — the same prompt indices are resampled for both arms in every replicate,
so shared item difficulty is held constant. The resample count and CI level are explicit parameters
recorded in the result (e3-0004 freezes them in the config).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.metrics import roc_auc_score


def auroc(scores: ArrayLike, labels: ArrayLike) -> float:
    """AUROC of ``scores`` against binary ``labels``. Fails closed if a class is absent."""
    y = np.asarray(labels)
    if len(np.unique(y)) < 2:
        raise ValueError("AUROC undefined: labels contain a single class")
    return float(roc_auc_score(y, np.asarray(scores, dtype=np.float64)))


@dataclass(frozen=True)
class PairedBootstrapResult:
    """Observed AUROC difference (arm A minus arm B) and its paired-bootstrap CI.

    ``diff`` is ``auroc(A) - auroc(B)`` on the full sample. ``ci_low``/``ci_high`` are the CI at
    ``ci_level`` from ``n_boot`` paired resamples. ``excludes_zero`` is True iff the whole CI lies
    on one side of zero — a positive-side exclusion is A beating B at this CI level.
    """

    diff: float
    ci_low: float
    ci_high: float
    n_boot: int
    ci_level: float
    excludes_zero: bool


def paired_bootstrap_auroc_diff(
    scores_a: ArrayLike,
    scores_b: ArrayLike,
    labels: ArrayLike,
    n_boot: int,
    ci_level: float,
    seed: int,
) -> PairedBootstrapResult:
    """Paired bootstrap of the AUROC difference between two arms over shared prompts.

    Args:
        scores_a, scores_b: per-prompt scores from the two arms (A is the probe, B the baseline).
        labels: per-prompt binary correctness labels.
        n_boot: number of paired resamples (recorded in the result).
        ci_level: central CI mass, e.g. 0.95 (recorded in the result).
        seed: seed for the resampling — the only randomness; fixed seed => identical CI.

    Each replicate draws one index set with replacement and applies it to A, B, and the labels
    together (paired). A replicate whose resampled labels are single-class is redrawn (AUROC would
    be undefined); the redraw budget is bounded and exhaustion fails closed rather than silently
    biasing the interval.
    """
    a = np.asarray(scores_a, dtype=np.float64)
    b = np.asarray(scores_b, dtype=np.float64)
    y = np.asarray(labels)
    n = y.shape[0]
    if not (a.shape[0] == b.shape[0] == n):
        raise ValueError("scores_a, scores_b, labels must be the same length")
    if not 0.0 < ci_level < 1.0:
        raise ValueError(f"ci_level must be in (0, 1); got {ci_level}")
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1")

    observed = auroc(a, y) - auroc(b, y)  # also validates both classes present

    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=np.float64)
    max_redraws = 1000
    for i in range(n_boot):
        for _ in range(max_redraws):
            idx = rng.integers(0, n, size=n)
            yi = y[idx]
            if len(np.unique(yi)) >= 2:
                break
        else:
            raise RuntimeError(
                "exhausted resample redraw budget: labels too imbalanced to bootstrap AUROC"
            )
        diffs[i] = roc_auc_score(yi, a[idx]) - roc_auc_score(yi, b[idx])

    lo_q = (1.0 - ci_level) / 2.0
    hi_q = 1.0 - lo_q
    ci_low = float(np.quantile(diffs, lo_q))
    ci_high = float(np.quantile(diffs, hi_q))
    return PairedBootstrapResult(
        diff=float(observed),
        ci_low=ci_low,
        ci_high=ci_high,
        n_boot=int(n_boot),
        ci_level=float(ci_level),
        excludes_zero=bool(ci_low > 0.0 or ci_high < 0.0),
    )
