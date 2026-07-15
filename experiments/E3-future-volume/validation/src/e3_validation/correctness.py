"""Correctness scoring protocol — frozen orientation, out-of-fold probe/B4, missing-VC rule (E).

Every arm (e3-0003) is turned into a per-item correctness score oriented so that HIGHER means
more-likely-correct, with the sign convention FROZEN here so the AUROC comparison cannot be silently
flipped between runs:

    probe       = -predicted_volume     (low reachable-future volume -> confident -> likely correct)
    B3          = -entropy              (low predictive entropy -> confident)
    B4          =  P(correct)           (logistic on the hidden state, the P(IK)-style probe)
    verbalized  =  stated_value         (B1, the 0-100 the model reports; missing -> NaN)

The probe and B4 scores MUST be out-of-fold: each item is scored by a model that never saw it, via
seeded k-fold cross-validation. There is deliberately **no in-sample scoring path** in this module —
scoring an item with a model fit on it would let correctness AUROC read the fit, not the signal.

Missing verbalized values (B1 parse failed twice, e3-0003) are carried as NaN. Any comparison that
INVOLVES the verbalized arm is computed on the VC-present subset only (a fair paired comparison needs
both arms defined on the same items); each arm's AUROC is reported on BOTH the full answerable subset
and the VC-present subset so the subsetting is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import KFold

from .compare import auroc
from .probe import DEFAULT_ALPHA_GRID, DEFAULT_INNER_FOLDS, select_alpha

#: The frozen orientation table — arm -> the sign/quantity convention. Recorded in the frozen config
#: (freeze.py) so a reader can confirm the AUROC comparison used exactly these orientations.
ORIENTATION: dict[str, str] = {
    "probe": "-predicted_volume",
    "b3": "-entropy",
    "b4": "P(correct)",
    "verbalized": "stated_value",
}


def _standardize(Xtr: NDArray[np.float64], Xev: NDArray[np.float64]) -> tuple[NDArray, NDArray]:
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd = np.where(sd == 0.0, 1.0, sd)
    return (Xtr - mu) / sd, (Xev - mu) / sd


def _kfold(n: int, k: int, seed: int) -> KFold:
    if not (2 <= k <= n):
        raise ValueError(f"k must be in [2, n]; got k={k}, n={n}")
    return KFold(n_splits=k, shuffle=True, random_state=seed)


def probe_scores_oof(
    X: ArrayLike,
    volume: ArrayLike,
    k: int,
    seed: int,
    alpha_grid: tuple[float, ...] = DEFAULT_ALPHA_GRID,
    inner_folds: int = DEFAULT_INNER_FOLDS,
) -> NDArray[np.float64]:
    """Out-of-fold probe correctness scores = ``-predicted_volume`` via seeded k-fold CV.

    Each fold: select ``alpha`` on the fold's training rows only (inner CV), fit the closed-form
    ridge, predict the held-out fold, negate. Every item is scored by a fold that never trained on it.
    """
    Xa = np.asarray(X, dtype=np.float64)
    ya = np.asarray(volume, dtype=np.float64)
    n = ya.shape[0]
    scores = np.empty(n, dtype=np.float64)
    for tr, te in _kfold(n, k, seed).split(Xa):
        alpha = select_alpha(Xa[tr], ya[tr], alpha_grid=alpha_grid, inner_folds=inner_folds)
        Xtr, Xte = _standardize(Xa[tr], Xa[te])
        model = Ridge(alpha=alpha).fit(Xtr, ya[tr])
        scores[te] = -model.predict(Xte)
    return scores


def b4_scores_oof(
    X: ArrayLike,
    correctness: ArrayLike,
    k: int,
    seed: int,
    C: float = 1.0,
) -> NDArray[np.float64]:
    """Out-of-fold B4 (P(IK)-style) correctness scores = ``P(correct)`` via seeded k-fold CV.

    A logistic probe trained directly on correctness labels from the hidden state; each item gets the
    held-out-fold predicted probability of correct. Requires both classes present in every fold's
    training rows (else the probe is undefined) — fails closed rather than emitting a constant.
    """
    Xa = np.asarray(X, dtype=np.float64)
    ya = np.asarray(correctness).astype(int)
    n = ya.shape[0]
    scores = np.empty(n, dtype=np.float64)
    for tr, te in _kfold(n, k, seed).split(Xa):
        if len(np.unique(ya[tr])) < 2:
            raise ValueError("a CV fold's training labels are single-class; B4 undefined")
        Xtr, Xte = _standardize(Xa[tr], Xa[te])
        clf = LogisticRegression(C=C, solver="lbfgs", max_iter=1000).fit(Xtr, ya[tr])
        pos = list(clf.classes_).index(1)
        scores[te] = clf.predict_proba(Xte)[:, pos]
    return scores


def b3_scores(entropy: ArrayLike) -> NDArray[np.float64]:
    """B3 correctness scores = ``-entropy`` (low predictive entropy -> confident)."""
    return -np.asarray(entropy, dtype=np.float64)


def verbalized_scores(stated: ArrayLike) -> NDArray[np.float64]:
    """Verbalized (B1) correctness scores = the stated 0-100 value; missing entries carried as NaN.

    Pass NaN (or None coerced upstream) for items whose B1 parse failed twice (e3-0003 missing rule).
    """
    return np.asarray(stated, dtype=np.float64)


def vc_present_mask(vc: ArrayLike) -> NDArray[np.bool_]:
    """Boolean mask of items with a present (non-NaN) verbalized value."""
    return ~np.isnan(np.asarray(vc, dtype=np.float64))


@dataclass(frozen=True)
class ArmAurocs:
    """An arm's AUROC on the full answerable subset and on the VC-present subset (both reported)."""

    full: float
    vc_present: float


def arm_aurocs(
    scores: ArrayLike, correctness: ArrayLike, vc_present: ArrayLike
) -> ArmAurocs:
    """Report one arm's correctness AUROC on the full answerable subset AND the VC-present subset.

    Both are reported so the missing-VC subsetting is transparent (an arm that looks strong only
    because the VC-present subset is easier is visible). Fails closed if either subset is single-class.
    """
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(correctness).astype(int)
    present = np.asarray(vc_present, dtype=bool)
    return ArmAurocs(full=auroc(s, y), vc_present=auroc(s[present], y[present]))
