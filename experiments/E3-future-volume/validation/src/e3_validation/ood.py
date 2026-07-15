"""Out-of-distribution transfer — leave-one-family-out, scored WITHIN the held-out family (D).

OOD is the load-bearing regime (e3-0001 § Evaluation (b); README Evaluation (c)): a probe that reads
a geometric quantity transfers across task families, a probe that found a dataset shortcut collapses.
The redesign fixes two flaws the old pooled-R^2 OOD number had, both surfaced by the rehearsal:

  * **Between-family mean structure inflated the pooled number.** Pooling every held-out prediction
    into one R^2 rewarded a probe that merely places each family at its correct mean level. This module
    scores the rank correlation INSIDE each held-out family (a single family carries no between-family
    means), so only genuine within-family transfer counts. The pooled statistic is the MEAN over
    rotations (pinned), and a per-rotation floor guards against one collapsing family being averaged
    away (rehearsal: factual transferred at +0.060 while the pool read +0.454).

  * **Extrapolation masqueraded as collapse.** If a held-out family's true-volume range extends beyond
    anything in training, the probe is being asked to extrapolate, not transfer — a distinct failure
    (REGISTRATION § 2: "transfer, not extrapolation"). This module flags ``range_uncovered`` per
    rotation so the verdict can route REFUTED_OOD_RANGE_UNCOVERED separately from REFUTED_OOD_FAILURE.

The gate bars (``ood_pooled_spearman_min``, ``ood_per_family_floor``) live on ``VerdictThresholds``;
this module invents none.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import spearmanr

from .probe import ridge_probe
from .splits import leave_one_family_out


def _spearman(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    return float(spearmanr(a, b)[0])


#: Default guard-band for the range-coverage check, as a fraction of the training span. Extrapolation
#: worth flagging is a whole missing diversity band (REGISTRATION § 2 "transfer, not extrapolation"),
#: not a single tail draw poking past the training max by a hair; this band tolerates finite-sample
#: tail noise while still catching a family-mean-sized gap. It is a numerical guard, not a
#: result-moving scientific threshold.
DEFAULT_COVERAGE_TOL_FRAC: float = 0.10


def range_uncovered(
    held_values: ArrayLike,
    train_values: ArrayLike,
    tol_frac: float = DEFAULT_COVERAGE_TOL_FRAC,
) -> bool:
    """True iff the held-out family's value range extends MATERIALLY beyond the training range.

    The guard-band is ``tol_frac`` times the training span, added symmetrically to the training
    range, so finite-sample tail noise (a held-out draw a hair past the training extreme) does not
    flag while a genuine extrapolation (a whole diversity band absent from training) does. ``tol_frac
    = 0.0`` recovers the strict containment check.
    """
    held = np.asarray(held_values, dtype=np.float64)
    train = np.asarray(train_values, dtype=np.float64)
    tr_min, tr_max = float(train.min()), float(train.max())
    tol = tol_frac * (tr_max - tr_min)
    return bool(held.min() < tr_min - tol or held.max() > tr_max + tol)


@dataclass(frozen=True)
class RotationResult:
    """One leave-one-family-out rotation."""

    held_out_family: object
    spearman: float
    n_held: int
    held_range: tuple[float, float]
    train_range: tuple[float, float]
    range_uncovered: bool


@dataclass(frozen=True)
class OODResult:
    """Aggregated leave-one-family-out transfer over all rotations.

    Fields feed the OOD ``VerdictInputs``: ``pooled_spearman`` (mean over rotations),
    ``min_rotation_spearman``, and ``any_range_uncovered``.
    """

    per_rotation: tuple[RotationResult, ...]
    pooled_spearman: float
    min_rotation_spearman: float
    any_range_uncovered: bool


def leave_one_family_out_spearman(
    X: ArrayLike,
    y: ArrayLike,
    family_labels: ArrayLike,
    range_tol_frac: float = DEFAULT_COVERAGE_TOL_FRAC,
) -> OODResult:
    """Fit the ridge probe leaving out each family in turn; score within-held-out-family Spearman.

    For each rotation the probe is trained on all other families and predicts the held-out family; the
    Spearman is computed between the held-out family's true volumes and the probe's predictions —
    entirely within that one family, so it cannot be earned by getting between-family levels right. The
    pooled statistic is the arithmetic mean over rotations (pinned); the minimum rotation is retained
    for the per-family floor; and each rotation's range coverage is checked.

    Requires >= 2 held-out items per rotation (Spearman undefined otherwise); raises if any family is
    too small, rather than silently dropping a rotation.
    """
    Xa = np.asarray(X, dtype=np.float64)
    ya = np.asarray(y, dtype=np.float64)
    fam = np.asarray(family_labels)

    rotations: list[RotationResult] = []
    for held, train_idx, test_idx in leave_one_family_out(fam):
        if test_idx.size < 2:
            raise ValueError(f"family {held!r} has < 2 items; within-family Spearman undefined")
        res = ridge_probe(Xa[train_idx], ya[train_idx], Xa[test_idx], ya[test_idx])
        sp = _spearman(ya[test_idx], res.predictions)
        held_vals = ya[test_idx]
        train_vals = ya[train_idx]
        rotations.append(
            RotationResult(
                held_out_family=held,
                spearman=sp,
                n_held=int(test_idx.size),
                held_range=(float(held_vals.min()), float(held_vals.max())),
                train_range=(float(train_vals.min()), float(train_vals.max())),
                range_uncovered=range_uncovered(held_vals, train_vals, tol_frac=range_tol_frac),
            )
        )

    spearmans = np.array([r.spearman for r in rotations], dtype=np.float64)
    return OODResult(
        per_rotation=tuple(rotations),
        pooled_spearman=float(spearmans.mean()),
        min_rotation_spearman=float(spearmans.min()),
        any_range_uncovered=bool(any(r.range_uncovered for r in rotations)),
    )
