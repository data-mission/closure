"""Two-part fidelity target and within-family fidelity (audit-driven redesign, B and C).

The rehearsal exposed two ways the old single continuous-fidelity number lied:

  * **A degenerate floor mass point.** Prompts whose N continuations are semantically identical hit
    the exact degenerate minimum ``N*log(epsilon)`` (11/41 in the rehearsal, 6/30 in the pilot). The
    log-volume target is therefore mixed discrete-continuous at the bottom of its range; a single R^2
    is pulled by the mass point. This module splits the degenerate-floor items out, reports a
    separate degeneracy classifier (is this prompt on the floor? — logistic on the hidden state,
    AUROC), and computes the CONTINUOUS fidelity (R^2 AND Spearman, each its own bar) on the
    non-degenerate subset only.

  * **A family-band / length confound.** Volume's between-family variance was large (η² = 0.255) and
    its rank correlation with mean continuation length was 0.910 — so a probe that reads "which family
    is this" or "how long will the reply be" reproduces most of the volume ranking without reading any
    dispersion geometry. This module residualizes the volume on train-derived family means and scores
    WITHIN families (rank correlation immune to between-family means), adds a family-mean-oracle margin
    (the probe must beat predict-by-family-mean), and offers the length-residualized within-family
    Spearman the length gate needs.

No numeric threshold is invented here; the bars live on ``VerdictThresholds``. The degenerate floor
value and epsilon are the e3-0002 constants (imported from ``volume``); ``degenerate_tol`` is a
numerical-equality tolerance, not a tuned bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import r2_score, roc_auc_score

from .volume import EPSILON

#: Tolerance for calling a volume "on the degenerate floor" (exact by construction; float slack only).
DEGENERATE_TOL: float = 1e-9


def _spearman(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    return float(spearmanr(a, b)[0])


def degenerate_floor(n_continuations: int, epsilon: float = EPSILON) -> float:
    """The degenerate-minimum volume ``N*log(epsilon)`` — all N continuations semantically identical
    -> centered Gram is the zero matrix -> ``log det(0 + epsilon I) = N*log(epsilon)`` (e3-0002)."""
    if n_continuations < 1:
        raise ValueError("n_continuations must be >= 1")
    return float(n_continuations) * float(np.log(epsilon))


def degenerate_mask(
    volumes: ArrayLike,
    n_continuations: int,
    epsilon: float = EPSILON,
    tol: float = DEGENERATE_TOL,
) -> NDArray[np.bool_]:
    """Boolean mask, True where a volume sits within ``tol`` of the ``N*log(epsilon)`` floor."""
    v = np.asarray(volumes, dtype=np.float64)
    floor = degenerate_floor(n_continuations, epsilon)
    return np.abs(v - floor) <= tol


def degeneracy_auroc(
    X_train: ArrayLike,
    deg_train: ArrayLike,
    X_eval: ArrayLike,
    deg_eval: ArrayLike,
    C: float = 1.0,
) -> float:
    """AUROC of a logistic probe (train-only standardizer) predicting the degenerate-floor indicator
    from the hidden state, reported SEPARATELY from continuous fidelity.

    Fails closed if either the train or the eval indicator is single-class (nothing to separate /
    AUROC undefined) — the caller reports "degeneracy not evaluable" rather than a fabricated number.
    """
    Xtr = np.asarray(X_train, dtype=np.float64)
    Xev = np.asarray(X_eval, dtype=np.float64)
    dtr = np.asarray(deg_train).astype(int)
    dev = np.asarray(deg_eval).astype(int)
    if len(np.unique(dtr)) < 2:
        raise ValueError("training degeneracy indicator is single-class; cannot fit a classifier")
    if len(np.unique(dev)) < 2:
        raise ValueError("eval degeneracy indicator is single-class; AUROC undefined")
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd = np.where(sd == 0.0, 1.0, sd)
    clf = LogisticRegression(C=C, solver="lbfgs", max_iter=1000).fit((Xtr - mu) / sd, dtr)
    scores = clf.decision_function((Xev - mu) / sd)
    return float(roc_auc_score(dev, scores))


def continuous_fidelity(
    predictions: ArrayLike,
    y_eval: ArrayLike,
    nondegenerate_mask: ArrayLike,
) -> tuple[float, float, int]:
    """R^2 and Spearman of ``predictions`` vs ``y_eval`` on the NON-degenerate subset only.

    Returns ``(r2, spearman, n_nondegenerate)``. Raises if fewer than two non-degenerate points
    survive (neither statistic is defined) — the caller reports not-evaluable rather than a number.
    """
    pred = np.asarray(predictions, dtype=np.float64)
    y = np.asarray(y_eval, dtype=np.float64)
    keep = np.asarray(nondegenerate_mask, dtype=bool)
    if pred.shape != y.shape or keep.shape != y.shape:
        raise ValueError("predictions, y_eval, nondegenerate_mask must share shape")
    n = int(keep.sum())
    if n < 2:
        raise ValueError(f"need >= 2 non-degenerate points for continuous fidelity; got {n}")
    return float(r2_score(y[keep], pred[keep])), _spearman(y[keep], pred[keep]), n


def _family_means(
    y_train: NDArray[np.float64], fam_train: NDArray[np.object_]
) -> tuple[dict[object, float], float]:
    global_mean = float(y_train.mean())
    means = {f: float(y_train[fam_train == f].mean()) for f in np.unique(fam_train)}
    return means, global_mean


def _apply_family_means(
    fam: NDArray[np.object_], means: dict[object, float], global_mean: float
) -> NDArray[np.float64]:
    return np.array([means.get(f, global_mean) for f in fam], dtype=np.float64)


def family_mean_oracle_r2(
    y_train: ArrayLike,
    y_eval: ArrayLike,
    fam_train: ArrayLike,
    fam_eval: ArrayLike,
) -> float:
    """R^2 of the family-mean oracle: predict each eval item by its family's TRAIN mean.

    This is the ceiling of purely between-family information about the volume — the family-band
    counterpart of ``probe.class_mean_predictor_r2`` (which uses the 2-bin sign class). The probe must
    beat this by ``family_oracle_margin_min`` to count as reading a within-family quantity rather than
    a family band. Unseen eval families fall back to the global train mean.
    """
    ytr = np.asarray(y_train, dtype=np.float64)
    yev = np.asarray(y_eval, dtype=np.float64)
    ftr = np.asarray(fam_train, dtype=object)
    fev = np.asarray(fam_eval, dtype=object)
    means, global_mean = _family_means(ytr, ftr)
    preds = _apply_family_means(fev, means, global_mean)
    return float(r2_score(yev, preds))


def within_family_metrics(
    predictions: ArrayLike,
    y_eval: ArrayLike,
    y_train: ArrayLike,
    fam_eval: ArrayLike,
    fam_train: ArrayLike,
    nondegenerate_mask: ArrayLike | None = None,
) -> tuple[float, float]:
    """Within-family R^2 and Spearman: residualize BOTH the true volume and the probe predictions on
    the train-derived family means, then correlate the residuals (optionally on the non-degenerate
    subset). This is immune to between-family mean structure — a probe that only separates families
    scores ~0 here, which is exactly the family-band confound the rehearsal flagged.

    Returns ``(within_family_r2, within_family_spearman)``.
    """
    pred = np.asarray(predictions, dtype=np.float64)
    yev = np.asarray(y_eval, dtype=np.float64)
    ytr = np.asarray(y_train, dtype=np.float64)
    fev = np.asarray(fam_eval, dtype=object)
    ftr = np.asarray(fam_train, dtype=object)
    means, global_mean = _family_means(ytr, ftr)
    center = _apply_family_means(fev, means, global_mean)
    resid_true = yev - center
    resid_pred = pred - center
    if nondegenerate_mask is not None:
        keep = np.asarray(nondegenerate_mask, dtype=bool)
        resid_true = resid_true[keep]
        resid_pred = resid_pred[keep]
    if resid_true.shape[0] < 2:
        raise ValueError("need >= 2 points for within-family metrics")
    return float(r2_score(resid_true, resid_pred)), _spearman(resid_true, resid_pred)


def _ols_fit_predict(
    y_train: NDArray[np.float64], F_train: NDArray[np.float64], F_eval: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Closed-form OLS with intercept, fit on train, predicted on eval (deterministic)."""
    Xtr = np.hstack([np.ones((F_train.shape[0], 1)), F_train])
    beta, *_ = np.linalg.lstsq(Xtr, y_train, rcond=None)
    Xev = np.hstack([np.ones((F_eval.shape[0], 1)), F_eval])
    return Xev @ beta


def length_residualized_volume(
    y_train: ArrayLike,
    y_eval: ArrayLike,
    len_train: ArrayLike,
    len_eval: ArrayLike,
) -> NDArray[np.float64]:
    """Residualize the eval volume on continuation-length features (mean and std length), using a
    train-fit OLS so no eval statistic leaks. ``len_train``/``len_eval`` are ``(n, 2)`` arrays of
    ``(mean_length, std_length)`` per prompt. Returns the eval volume minus its length prediction.
    """
    ytr = np.asarray(y_train, dtype=np.float64)
    yev = np.asarray(y_eval, dtype=np.float64)
    Ltr = np.asarray(len_train, dtype=np.float64)
    Lev = np.asarray(len_eval, dtype=np.float64)
    if Ltr.ndim != 2 or Ltr.shape[1] != 2 or Lev.shape[1] != 2:
        raise ValueError("len_train/len_eval must be (n, 2): (mean_length, std_length)")
    pred = _ols_fit_predict(ytr, Ltr, Lev)
    return yev - pred


def length_residualized_within_family_spearman(
    predictions: ArrayLike,
    y_eval: ArrayLike,
    y_train: ArrayLike,
    fam_eval: ArrayLike,
    fam_train: ArrayLike,
    len_train: ArrayLike,
    len_eval: ArrayLike,
    nondegenerate_mask: ArrayLike | None = None,
) -> float:
    """Within-family Spearman of the probe predictions against the LENGTH-RESIDUALIZED volume.

    The volume is first stripped of its linear dependence on continuation length (train-fit), then the
    within-family residual-on-family-mean Spearman is computed as in ``within_family_metrics``. If the
    probe was reading verbosity rather than geometry (ρ(volume, length) = 0.910 on the rehearsal set),
    removing length collapses this Spearman — the signal the length gate is designed to catch.
    """
    len_resid_vol = length_residualized_volume(y_train, y_eval, len_train, len_eval)
    # The train targets for family-mean residualization must be on the same length-residual scale.
    len_resid_train = length_residualized_volume(y_train, y_train, len_train, len_train)
    _, spearman = within_family_metrics(
        predictions,
        len_resid_vol,
        len_resid_train,
        fam_eval,
        fam_train,
        nondegenerate_mask=nondegenerate_mask,
    )
    return spearman


@dataclass(frozen=True)
class FidelityResult:
    """Bundle of the two-part and within-family fidelity quantities for one evaluation split.

    Feeds the correspondingly-named ``VerdictInputs`` fields. ``degeneracy_auroc`` is None when the
    degeneracy indicator was single-class on this split (reported as not-evaluable, not fabricated).
    """

    r2_nondegenerate: float
    spearman_nondegenerate: float
    n_nondegenerate: int
    n_degenerate: int
    degeneracy_auroc: float | None
    within_family_r2: float
    within_family_spearman: float
    family_oracle_r2: float
    family_oracle_margin: float
    within_family_spearman_length_resid: float
