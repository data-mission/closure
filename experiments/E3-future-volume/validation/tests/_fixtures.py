"""Seeded, in-code fixture generators — the planted-answer data for the E3 synthetic validation.

Every generator is a pure function of an explicit seed; **no data blob is committed** (mirrors
`harness/tests/conftest.py` and E0 PLAN step 4). Each generator's docstring states the answer it
plants *by construction*, and the tests assert that the pipeline recovers exactly that answer. All
of this data is throwaway: it exists only to prove the analysis pipeline and the verdict-branch
logic cannot lie, before any real corpus exists.

Class labels used for the oracle class-mean predictor and for reasoning about the median split are
`(y > 0)` — the binarized information ceiling a SEP-style probe could exploit.
"""

from __future__ import annotations

import numpy as np

from e3_validation.verdict import VerdictThresholds


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def sign_class(y: np.ndarray) -> np.ndarray:
    """Binary class label ``(y > 0)`` — the class a binarized probe can read."""
    return (np.asarray(y) > 0.0).astype(int)


# ---------------------------------------------------------------------------------------------
# Throwaway verdict thresholds for the synthetic stage.
#
# These are NOT the registration values. verdict.py invents no threshold; the registration
# (e3-0004 freeze) fixes the real numbers before any real datum exists. These exist ONLY to route
# each planted fixture to its known-correct branch, and they sit well clear of every fixture's
# observed metrics (see VALIDATION.md), so the routing is not knife-edge.
# ---------------------------------------------------------------------------------------------
PASSING_THRESHOLDS = VerdictThresholds(
    r2_fidelity_min=0.50,
    r2_margin_over_classmean_min=0.10,
    r2_ood_min=0.50,
    auc_binary_min=0.70,
    vc_ci_floor=0.0,
)


def make_linear_signal(
    seed: int = 101, n_per_family: int = 80, n_families: int = 4, dim: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture A. ``y = w . x + small noise`` with the SAME signal direction ``w`` in every family.

    Planted answer: the ridge probe recovers ``w``, so R^2 and Spearman are ~1 both in-distribution
    AND out-of-distribution — the signal is identical across families, so leave-one-family-out
    transfers. Families differ only by a nuisance offset in a direction **orthogonal to ``w``**, so
    the families are distinguishable but the regression target is family-invariant. The class-mean
    predictor explains only the between-class variance, so the continuous probe materially exceeds
    it. Verdict (with passing OOD and beats-VC): confirmed-shaped.
    """
    rng = np.random.default_rng(seed)
    w = _unit(rng.standard_normal(dim))
    xs, ys, fams = [], [], []
    for f in range(n_families):
        xf = rng.standard_normal((n_per_family, dim))
        off = rng.standard_normal(dim)
        off -= (off @ w) * w  # orthogonalize the nuisance offset to the signal direction
        off = _unit(off)
        xf += (f - (n_families - 1) / 2.0) * 3.0 * off
        yf = xf @ w + 0.05 * rng.standard_normal(n_per_family)  # small noise
        xs.append(xf)
        ys.append(yf)
        fams.append(np.full(n_per_family, f))
    return np.vstack(xs), np.concatenate(ys), np.concatenate(fams)


def make_verbalized_confidence_arms(
    seed: int = 7, n: int = 240
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture A companion: a probe correctness arm that beats a weak verbalized-confidence arm.

    Planted answer: ``probe_scores`` separate the binary correctness label strongly; ``vc_scores``
    separate it weakly, so the paired-bootstrap AUROC margin (probe minus verbalized) is positive
    and its CI excludes zero. Returns ``(probe_scores, vc_scores, correctness)``.
    """
    rng = np.random.default_rng(seed)
    correctness = rng.integers(0, 2, n)
    probe_scores = correctness + rng.normal(0.0, 0.7, n)  # strong predictor
    vc_scores = correctness + rng.normal(0.0, 2.5, n)  # weak predictor
    return probe_scores, vc_scores, correctness


def make_no_signal(
    seed: int = 202, n: int = 240, dim: int = 20
) -> tuple[np.ndarray, np.ndarray]:
    """Fixture B. ``y`` drawn independently of ``x``.

    Planted answer: no map from ``x`` to ``y`` exists, so held-out R^2 is ~0 (must not be
    manufactured positive) and the binarized median-split AUROC is ~0.5. Verdict: refuted/no-signal.
    """
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, dim)), rng.standard_normal(n)


def make_binary_only(
    seed: int = 303, n: int = 300, dim: int = 20, base: float = 2.0, mag: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture C. ``x`` linearly encodes only the class (sign) of ``y``; within-class magnitude is
    independent of ``x``.

    Construction: ``x = c * u * mag + isotropic noise`` (so ``x`` carries the class ``c = +/-1``),
    and ``y = c * base + within_class_noise`` where the within-class noise is independent of ``x``.
    Planted answer: the logistic median-split probe reads the class well (AUROC high), but the
    continuous ridge R^2 does NOT materially exceed the oracle class-mean predictor — everything
    ``x`` says about ``y`` is the class, and the magnitude within a class is unreadable. This is the
    discriminating case: signal exists only at binary granularity (already known from SEP). Verdict:
    refuted/binary-only. Returns ``(X, y, c)``.
    """
    rng = np.random.default_rng(seed)
    c = rng.choice([-1.0, 1.0], n)
    u = _unit(rng.standard_normal(dim))
    x = c[:, None] * u[None, :] * mag + rng.standard_normal((n, dim))
    y = c * base + rng.normal(0.0, 1.0, n)  # magnitude within class independent of x
    return x, y, c


def make_ood_shortcut(
    seed: int = 404, n_per_family: int = 80, n_families: int = 5, dim_signal: int = 5, big: float = 10.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture E. A family-correlated nuisance direction predicts ``y`` within training families but
    is broken in the held-out family, and the nuisance variance dominates the true signal.

    Construction: the true signal ``0.3 * (x_sig . w)`` is weak; each family ``f`` carries a distinct
    constant ``family_mean_f`` spanning [-5, 5] (large variance) that is encoded ONLY in a
    family-specific indicator coordinate set to ``big``. In-distribution (random split over all
    families) the probe learns each family's indicator -> family_mean map and R^2 is ~1 — the
    shortcut. Leave-one-family-out breaks it: the held-out family's indicator coordinate is constant
    zero across all training rows, so the fitted coefficient on it is inert and the probe cannot
    recover that family's mean -> pooled OOD R^2 collapses far below zero. Ridge provably prefers the
    high-variance shortcut in-distribution over the weak true signal. Verdict: refuted/ood-failure.
    Returns ``(X, y, family_labels)``.
    """
    rng = np.random.default_rng(seed)
    w = _unit(rng.standard_normal(dim_signal))
    family_means = np.linspace(-5.0, 5.0, n_families)
    dim = dim_signal + n_families
    xs, ys, fams = [], [], []
    for f in range(n_families):
        x_sig = rng.standard_normal((n_per_family, dim_signal))
        y = 0.3 * (x_sig @ w) + family_means[f] + 0.05 * rng.standard_normal(n_per_family)
        xf = np.zeros((n_per_family, dim))
        xf[:, :dim_signal] = x_sig
        xf[:, dim_signal + f] = big  # family-specific shortcut coordinate
        xs.append(xf)
        ys.append(y)
        fams.append(np.full(n_per_family, f))
    return np.vstack(xs), np.concatenate(ys), np.concatenate(fams)


def dispersion_family(s: float, n: int = 6, dim: int = 12) -> np.ndarray:
    """Fixture D helper: N points on a shared line plus a growing orthogonal spread ``s``.

    Planted answer: at ``s = 0`` all centered points are collinear (rank 1 -> minimal volume); as
    ``s`` grows the points occupy more orthogonal dimensions, so ``semantic_volume`` is strictly
    increasing in ``s``. (Because the statistic L2-normalizes each centered vector, "more
    dispersion" must add orthogonal extent, not merely scale — which is what ``s`` does here.)
    """
    a = np.linspace(-1.0, 1.0, n)
    x = np.zeros((n, dim))
    x[:, 0] = a  # shared line direction
    for i in range(n):
        x[i, i + 1] = s  # per-point orthogonal spread, magnitude s
    return x
