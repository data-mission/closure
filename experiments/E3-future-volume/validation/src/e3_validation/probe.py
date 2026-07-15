"""Probes: ridge regression of continuous volume, and the SEP-style logistic median-split baseline.

Ridge probe (e3-0001):
    - z-score standardizer fit on the **training split only**, applied unchanged to every eval split;
    - regularization strength ``alpha`` selected by inner k-fold cross-validation on the training
      split only, over a pre-registered log-spaced grid — never re-chosen after seeing held-out or
      OOD performance;
    - closed-form (deterministic) ridge fit — the exactly-reproducible algorithmic step of e3-0004;
    - reports R^2 and Spearman rank correlation on any eval split.

Logistic median-split probe (B2 of e3-0003):
    - the **median-split** (high/low) class of the volume, median computed on the **training split
      only**, is the SEP-style binarized target (arXiv:2406.15927);
    - same input vector and train-only standardizer as the ridge probe (a fair binarized counterpart);
    - reports AUROC on the eval split.

The pre-registered ``alpha`` grid and inner-fold count are module defaults here for the synthetic
stage; e3-0004 freezes their real values in the config before any real data is fit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import KFold

#: Pre-registered log-spaced ridge-alpha grid (placeholder for the synthetic stage; e3-0004 freezes
#: the confirmatory grid). Log-spaced per e3-0001.
DEFAULT_ALPHA_GRID: tuple[float, ...] = tuple(np.logspace(-3.0, 3.0, 13))

#: Inner-CV fold count for alpha selection on the training split (e3-0001).
DEFAULT_INNER_FOLDS: int = 5


@dataclass(frozen=True)
class RidgeProbeResult:
    """Outcome of one ridge-probe fit-and-score."""

    alpha: float
    r2: float
    spearman: float
    predictions: NDArray[np.float64]


@dataclass(frozen=True)
class LogisticProbeResult:
    """Outcome of one logistic median-split (SEP-style) probe fit-and-score."""

    threshold: float
    auroc: float


def _standardizer(X_train: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Per-dimension mean and std estimated on the training split only (e3-0001 leakage guard).

    A zero-variance feature is standardized by 1.0 (leaving it centered but unscaled) rather than
    dividing by zero.
    """
    mu = X_train.mean(axis=0)
    sd = X_train.std(axis=0)
    sd = np.where(sd == 0.0, 1.0, sd)
    return mu, sd


def _spearman(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    # scipy renamed the attribute across versions; index [0] is stable.
    return float(spearmanr(a, b)[0])


def select_alpha(
    X_train: ArrayLike,
    y_train: ArrayLike,
    alpha_grid: tuple[float, ...] = DEFAULT_ALPHA_GRID,
    inner_folds: int = DEFAULT_INNER_FOLDS,
) -> float:
    """Select ``alpha`` by inner k-fold CV on the training split only (mean fold R^2).

    Deterministic: ``KFold(shuffle=False)`` and the closed-form ridge fit carry no randomness. The
    standardizer is refit inside each inner fold on that fold's training rows only, so the inner-CV
    score is itself leakage-free.
    """
    Xtr = np.asarray(X_train, dtype=np.float64)
    ytr = np.asarray(y_train, dtype=np.float64)
    kf = KFold(n_splits=inner_folds, shuffle=False)

    best_alpha = float(alpha_grid[0])
    best_score = -np.inf
    for alpha in alpha_grid:
        fold_scores: list[float] = []
        for tr, va in kf.split(Xtr):
            mu, sd = _standardizer(Xtr[tr])
            model = Ridge(alpha=alpha).fit((Xtr[tr] - mu) / sd, ytr[tr])
            pred = model.predict((Xtr[va] - mu) / sd)
            fold_scores.append(r2_score(ytr[va], pred))
        mean_score = float(np.mean(fold_scores))
        if mean_score > best_score:
            best_score = mean_score
            best_alpha = float(alpha)
    return best_alpha


def ridge_probe(
    X_train: ArrayLike,
    y_train: ArrayLike,
    X_eval: ArrayLike,
    y_eval: ArrayLike,
    alpha_grid: tuple[float, ...] = DEFAULT_ALPHA_GRID,
    inner_folds: int = DEFAULT_INNER_FOLDS,
) -> RidgeProbeResult:
    """Fit the ridge probe on (X_train, y_train), score R^2 and Spearman on (X_eval, y_eval)."""
    Xtr = np.asarray(X_train, dtype=np.float64)
    ytr = np.asarray(y_train, dtype=np.float64)
    Xev = np.asarray(X_eval, dtype=np.float64)
    yev = np.asarray(y_eval, dtype=np.float64)

    alpha = select_alpha(Xtr, ytr, alpha_grid=alpha_grid, inner_folds=inner_folds)
    mu, sd = _standardizer(Xtr)  # train-only fit, applied to eval unchanged
    model = Ridge(alpha=alpha).fit((Xtr - mu) / sd, ytr)
    pred = model.predict((Xev - mu) / sd)
    return RidgeProbeResult(
        alpha=alpha,
        r2=float(r2_score(yev, pred)),
        spearman=_spearman(yev, pred),
        predictions=pred,
    )


def logistic_median_split_probe(
    X_train: ArrayLike,
    y_train: ArrayLike,
    X_eval: ArrayLike,
    y_eval: ArrayLike,
    C: float = 1.0,
) -> LogisticProbeResult:
    """Fit a logistic probe on the train-median-split class of the volume; report eval AUROC (B2).

    The split threshold is the **training** median; the same threshold labels the eval split, so no
    eval statistic leaks into the target. Fails closed if either class is absent from the training
    labels (nothing to separate) or from the eval labels (AUROC undefined).
    """
    Xtr = np.asarray(X_train, dtype=np.float64)
    ytr = np.asarray(y_train, dtype=np.float64)
    Xev = np.asarray(X_eval, dtype=np.float64)
    yev = np.asarray(y_eval, dtype=np.float64)

    threshold = float(np.median(ytr))
    ytr_bin = (ytr > threshold).astype(int)
    yev_bin = (yev > threshold).astype(int)
    if len(np.unique(ytr_bin)) < 2:
        raise ValueError("training median-split has a single class; cannot fit a binarized probe")
    if len(np.unique(yev_bin)) < 2:
        raise ValueError("eval median-split has a single class; AUROC is undefined")

    mu, sd = _standardizer(Xtr)
    clf = LogisticRegression(C=C, solver="lbfgs", max_iter=1000).fit((Xtr - mu) / sd, ytr_bin)
    scores = clf.decision_function((Xev - mu) / sd)
    return LogisticProbeResult(threshold=threshold, auroc=float(roc_auc_score(yev_bin, scores)))


def class_mean_predictor_r2(
    y_train: ArrayLike,
    y_eval: ArrayLike,
    class_train: ArrayLike,
    class_eval: ArrayLike,
) -> float:
    """R^2 of an oracle class-mean predictor: predict each eval point by its class's train mean.

    This is the ceiling of what a purely **binarized** (class-only) signal can explain about the
    continuous volume — it is handed the true class of each eval point and predicts the
    class-conditional training mean. The continuous ridge probe having R^2 that does **not**
    materially exceed this value is exactly the "signal exists only at binary granularity" branch
    (README § Verdict conditions; e3-0003 B2): the probe read nothing beyond the class. Unseen eval
    classes fall back to the global training mean.
    """
    ytr = np.asarray(y_train, dtype=np.float64)
    yev = np.asarray(y_eval, dtype=np.float64)
    ctr = np.asarray(class_train)
    cev = np.asarray(class_eval)

    global_mean = float(ytr.mean())
    means = {c: float(ytr[ctr == c].mean()) for c in np.unique(ctr)}
    preds = np.array([means.get(c, global_mean) for c in cev], dtype=np.float64)
    return float(r2_score(yev, preds))
