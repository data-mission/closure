"""Ground-truth semantic volume (e3-0002).

For a prompt's N continuation embeddings the volume statistic is::

    log det(G + epsilon * I)

where G is the N x N Gram matrix of the N embeddings after they are **mean-centered and then
L2-normalized**, and ``epsilon = 1e-6`` is the pre-registered rank-safety ridge (mean-centering N
vectors drops the Gram rank by exactly one, so the raw centered Gram is singular and its
log-determinant is -inf; the fixed epsilon makes the determinant finite without materially moving
the well-conditioned directions). See e3-0002 § Decision.

Order note (per the task's ambiguity clause): e3-0002 states "mean-center the N vectors,
L2-normalize them, form the N x N Gram matrix" — centering **before** normalization. That is the
order implemented here. It is not ambiguous in the record, but it is the choice flagged in the
report either way.

All arithmetic is float64. The volume computation is one of the two "purely algorithmic" steps
e3-0004 claims is *exactly* reproducible on fixed inputs (the other is the closed-form ridge fit);
the tests assert bit-identical output across repeated runs.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

#: Pre-registered rank-safety ridge (e3-0002). Not a tuned hyperparameter.
EPSILON: float = 1e-6


def _mean_center(X: NDArray[np.float64]) -> NDArray[np.float64]:
    """Subtract the per-dimension mean over the N rows (the continuations)."""
    return X - X.mean(axis=0, keepdims=True)


def _l2_normalize(X: NDArray[np.float64]) -> NDArray[np.float64]:
    """Scale each row to unit L2 norm. Zero rows are left as zero (0/0 is not manufactured).

    A row can be exactly zero after mean-centering when all continuations are identical: every
    centered vector is the zero vector. Dividing by a guarded norm of 1.0 keeps those rows zero,
    so the Gram matrix is exactly the zero matrix and the volume is ``N * log(epsilon)`` — the
    hand-computed degenerate minimum (fixture D).
    """
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    safe = np.where(norms == 0.0, 1.0, norms)
    return X / safe


def semantic_volume(embeddings: ArrayLike, epsilon: float = EPSILON) -> float:
    """Return ``log det(G + epsilon I)`` for the mean-centered, L2-normalized embeddings.

    Args:
        embeddings: array of shape (N, D) — N continuation embeddings of dimension D.
        epsilon: rank-safety ridge added to the Gram diagonal. Defaults to the pre-registered
            ``EPSILON`` (1e-6). Exposed only so fixture D can probe epsilon-stability; never tuned
            on real prompts (e3-0002).

    Returns:
        The scalar log-determinant volume (float).

    Fails closed: raises on a non-2-D input or N < 1. A ``slogdet`` sign of exactly 0 (a singular
    matrix — only reachable when ``epsilon`` is effectively 0, since the registered 1e-6 makes the
    ridged Gram strictly positive definite) yields the mathematically correct ``-inf``. A **negative**
    sign is impossible for a symmetric positive-semidefinite Gram plus a non-negative ridge, so it
    signals numerical corruption (NaN/inf in the embeddings) and is refused rather than returned.
    """
    X = np.asarray(embeddings, dtype=np.float64)
    if X.ndim != 2:
        raise ValueError(f"embeddings must be 2-D (N, D); got shape {X.shape}")
    n = X.shape[0]
    if n < 1:
        raise ValueError("need at least one embedding")

    Xn = _l2_normalize(_mean_center(X))  # center THEN normalize (e3-0002 order)
    gram = Xn @ Xn.T
    ridged = gram + epsilon * np.eye(n)
    sign, logabsdet = np.linalg.slogdet(ridged)
    if sign < 0.0:
        raise FloatingPointError(
            f"ridged Gram has negative slogdet sign {sign} — impossible for a PSD Gram plus a "
            "non-negative ridge; embeddings are numerically corrupt (NaN/inf), refusing a volume"
        )
    return float(logabsdet)
