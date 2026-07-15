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

from e3_validation.verdict import VerdictInputs, VerdictThresholds


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def sign_class(y: np.ndarray) -> np.ndarray:
    """Binary class label ``(y > 0)`` — the class a binarized probe can read."""
    return (np.asarray(y) > 0.0).astype(int)


# ---------------------------------------------------------------------------------------------
# Throwaway verdict thresholds for the synthetic stage (audit-driven redesign — full param set).
#
# These are NOT the registration values. verdict.py invents no threshold; the registration
# (e3-0004 freeze) fixes the real numbers before any real datum exists. These exist ONLY to route
# each planted fixture to its known-correct branch, and they sit well clear of every fixture's
# observed metrics (see VALIDATION.md), so the routing is not knife-edge.
# ---------------------------------------------------------------------------------------------
PASSING_THRESHOLDS = VerdictThresholds(
    min_negatives=20,
    r2_fidelity_min=0.50,
    spearman_fidelity_min=0.50,
    within_family_spearman_min=0.50,
    family_oracle_margin_min=0.10,
    r2_margin_over_classmean_min=0.10,
    ood_pooled_spearman_min=0.50,
    ood_per_family_floor=0.30,
    auc_binary_min=0.70,
    vc_ci_floor=0.0,
    b3_ci_floor=0.0,
    b4_margin_ceiling=0.0,
    require_length_robust=True,
)


def passing_inputs(**overrides) -> VerdictInputs:
    """A fully gate-satisfying ``VerdictInputs`` (routes to confirmed-shaped under PASSING_THRESHOLDS),
    with keyword overrides so a test can vary ONE dimension at a time to reach a target branch.

    The base values sit well clear of every PASSING_THRESHOLDS bar. This helper exists only so the
    branch-logic unit tests can plant a single failing metric; the real pipeline populates every field
    from measured quantities (see the integration-style fixtures in the pipeline test modules).
    """
    base = dict(
        n_negatives=40,
        r2_nondegenerate=0.90,
        spearman_nondegenerate=0.90,
        n_nondegenerate=95,
        n_degenerate=5,
        degeneracy_auroc=0.99,
        within_family_spearman=0.85,
        within_family_r2=0.80,
        family_oracle_r2=0.50,
        family_oracle_margin=0.35,
        within_family_spearman_length_resid=0.80,
        r2_indist=0.90,
        r2_classmean_indist=0.40,
        auc_binary=0.95,
        ood_pooled_spearman=0.80,
        ood_min_rotation_spearman=0.60,
        ood_range_uncovered=False,
        probe_vs_vc_ci_low=0.10,
        probe_vs_b3_ci_low=0.10,
        b4_vs_probe_ci_low=-0.05,
    )
    base.update(overrides)
    return VerdictInputs(**base)


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


def make_family_band_only(
    seed: int = 505, n_per_family: int = 90, n_families: int = 4, dim: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture F1 (the fixture the old suite LACKED). Heterogeneous family means, NO within-family
    signal: ``y = family_mean_f + within_family_noise`` with the within-family noise independent of
    ``x``; ``x`` encodes only the family (a family-indicator coordinate plus isotropic noise).

    Planted answer: the probe can predict each family's mean (between-family structure is readable),
    so a pooled/full R² and a median-split AUROC look strong — BUT residualizing the volume on the
    family mean leaves pure noise uncorrelated with ``x``, so the WITHIN-family Spearman is ~0 and the
    family-mean-oracle margin is ~0. This is exactly the family-band confound the redesign's
    within-family gates are built to catch: the fixture MUST fail the within-family fidelity gates and
    route refuted, never confirmed-shaped. Returns ``(X, y, family_labels)``.
    """
    rng = np.random.default_rng(seed)
    family_means = np.linspace(-5.0, 5.0, n_families)
    xs, ys, fams = [], [], []
    for f in range(n_families):
        x = rng.standard_normal((n_per_family, dim))
        x[:, f] += 6.0  # family-indicator coordinate — x carries the family, nothing more
        y = family_means[f] + rng.standard_normal(n_per_family)  # within-family noise ⟂ x
        xs.append(x)
        ys.append(y)
        fams.append(np.full(n_per_family, f))
    return np.vstack(xs), np.concatenate(ys), np.concatenate(fams)


def make_family_specific_signal(
    seed: int = 606, n_per_family: int = 90, n_families: int = 4, block: int = 4
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture F2 — genuine within-family signal that does NOT transfer OOD. Each family's signal
    lives in its OWN coordinate block: ``y = x[:, block_f] · w_f + noise``; other blocks are noise for
    that family.

    Planted answer: in-distribution (a random split that includes every family in training) the probe
    learns each block's coefficient, so in-distribution fidelity and within-family Spearman are high.
    But under leave-one-family-out the held-out family's block was pure noise in every training family,
    so its coefficient is ~0 and the probe cannot read the held-out family's within-family signal —
    the within-held-out-family Spearman collapses. This is a GENUINE OOD failure (unlike the family-
    band fixture, the in-distribution signal is real), and the volume ranges match across families
    (all ``y ~ N(0, ~1)``), so it is a collapse, not an uncovered-range extrapolation. Returns
    ``(X, y, family_labels)``.
    """
    rng = np.random.default_rng(seed)
    dim = n_families * block
    xs, ys, fams = [], [], []
    for f in range(n_families):
        # Small isotropic base noise EVERYWHERE (so no feature is exactly constant-zero in any
        # training set), plus a strong signal placed only in this family's own block.
        x = 0.3 * rng.standard_normal((n_per_family, dim))
        sig = rng.standard_normal((n_per_family, block))
        x[:, f * block : (f + 1) * block] += sig
        w_f = _unit(rng.standard_normal(block))
        y = sig @ w_f + 0.05 * rng.standard_normal(n_per_family)
        xs.append(x)
        ys.append(y)
        fams.append(np.full(n_per_family, f))
    return np.vstack(xs), np.concatenate(ys), np.concatenate(fams)


def make_degenerate_mixed(
    seed: int = 707,
    n: int = 300,
    dim: int = 20,
    n_continuations: int = 10,
    epsilon: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fixture F3 — a mixed discrete-continuous volume target with a degenerate-floor mass point.

    About half the items sit on the exact degenerate minimum ``N·log(epsilon)`` (all continuations
    identical); the rest carry a continuous volume. ``x`` encodes BOTH: one direction separates the
    degenerate items (so the degeneracy classifier's AUROC is high) and an orthogonal direction
    encodes the continuous value (so the ridge probe recovers it on the non-degenerate subset).

    Planted answer: ``degenerate_mask`` recovers the floor items exactly; the degeneracy classifier
    AUROC is high; and continuous R²/Spearman on the NON-degenerate subset are high — the two-part
    treatment separates the mass point from the continuous fidelity. Returns ``(X, y, is_degenerate)``.
    """
    rng = np.random.default_rng(seed)
    floor = float(n_continuations) * float(np.log(epsilon))
    is_deg = rng.integers(0, 2, n).astype(bool)
    cont = rng.uniform(-100.0, -20.0, n)  # continuous volume for non-degenerate items
    y = np.where(is_deg, floor, cont)
    w_deg = _unit(rng.standard_normal(dim))
    w_vol = rng.standard_normal(dim)
    w_vol -= (w_vol @ w_deg) * w_deg
    w_vol = _unit(w_vol)
    # The two populations are encoded CLEANLY and disjointly: degenerate items carry only the
    # degeneracy direction (target = floor), non-degenerate items carry only the continuous-value
    # direction (target = their continuous volume). This avoids planting a spurious continuous signal
    # on floor items — whose target is the constant floor — which would corrupt the ridge fit.
    x = 0.7 * rng.standard_normal((n, dim))
    x[is_deg] += w_deg[None, :] * 5.0
    nd = ~is_deg
    x[nd] += (cont[nd] - cont[nd].mean())[:, None] * w_vol[None, :] * 0.3
    return x, y, is_deg


def make_length_confound(
    seed: int = 808, n_per_family: int = 90, n_families: int = 4, dim: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fixture F4 — volume is (almost) a linear readout of continuation length; the probe reads length.

    Per prompt a mean and std continuation length are drawn; the volume is
    ``a·mean_len + b·std_len + family_mean_f + tiny_noise`` and ``x`` linearly encodes the two length
    quantities. So the probe predicts volume well BY reading length, and the within-family Spearman
    (before length control) is high.

    Planted answer: within-family fidelity holds — until the volume is residualized on length, after
    which only ``tiny_noise`` remains and the within-family Spearman collapses. The length gate MUST
    fire (REFUTED_LENGTH_CONFOUNDED) even though every un-controlled fidelity metric passes; this is
    the ρ(volume, length)=0.910 hazard the rehearsal flagged, planted. Returns
    ``(X, y, family_labels, length_features)`` where ``length_features`` is ``(n, 2)`` of
    ``(mean_length, std_length)``.
    """
    rng = np.random.default_rng(seed)
    family_means = np.linspace(-3.0, 3.0, n_families)
    xs, ys, fams, lens = [], [], [], []
    for f in range(n_families):
        mean_len = rng.uniform(20.0, 200.0, n_per_family)
        std_len = rng.uniform(1.0, 40.0, n_per_family)
        y = 0.5 * mean_len + 0.3 * std_len + family_means[f] + 0.01 * rng.standard_normal(n_per_family)
        x = rng.standard_normal((n_per_family, dim))
        # encode the two length quantities into x (standardized magnitudes for readability)
        x[:, 0] = (mean_len - 110.0) / 52.0
        x[:, 1] = (std_len - 20.0) / 11.0
        xs.append(x)
        ys.append(y)
        fams.append(np.full(n_per_family, f))
        lens.append(np.column_stack([mean_len, std_len]))
    return np.vstack(xs), np.concatenate(ys), np.concatenate(fams), np.vstack(lens)


def make_correctness_arms(
    seed: int = 909, n: int = 260, dim: int = 16, n_missing_vc: int = 40
) -> dict:
    """Fixture F5 — a full correctness-arm bundle for the added-value gates.

    Constructs hidden states ``X``, a continuous ``volume`` (low volume ⇒ correct), binary
    ``correctness``, predictive ``entropy`` (low ⇒ correct), and verbalized ``vc`` values with
    ``n_missing_vc`` NaN entries. By construction the volume probe and B3 entropy separate correctness
    strongly, B4 (correctness probe) is comparable-but-not-better than the probe, and verbalized
    confidence is weak and near-constant (the literature/rehearsal pattern).

    Planted answer: out-of-fold probe scores beat both verbalized (on the VC-present subset) and B3,
    and B4 does not significantly beat the probe. Returns a dict of arrays.
    """
    rng = np.random.default_rng(seed)
    correctness = rng.integers(0, 2, n)
    # low volume for correct items (probe reads volume; oriented -volume ⇒ correct)
    volume = np.where(correctness == 1, -90.0, -20.0) + rng.normal(0.0, 10.0, n)
    entropy = np.where(correctness == 1, 0.6, 1.4) + rng.normal(0.0, 0.6, n)  # low entropy ⇒ correct
    w = _unit(rng.standard_normal(dim))
    # X encodes the volume signal strongly (so the OOF ridge recovers it) plus isotropic noise
    X = (volume - volume.mean())[:, None] * w[None, :] * 0.10 + rng.standard_normal((n, dim))
    vc = np.where(correctness == 1, 96.0, 92.0) + rng.normal(0.0, 6.0, n)  # weak, near-constant
    vc = np.clip(vc, 0.0, 100.0)
    miss = rng.choice(n, size=n_missing_vc, replace=False)
    vc[miss] = np.nan
    return {
        "X": X,
        "volume": volume,
        "correctness": correctness,
        "entropy": entropy,
        "vc": vc,
    }


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
