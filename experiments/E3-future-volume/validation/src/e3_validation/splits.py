"""Evaluation regimes (e3-0001).

Two regimes:

(a) **in-distribution** — held-out prompts drawn from the same task families as training (a seeded
    random split), scored by R^2 / Spearman; the regression-fidelity number of README Evaluation (a).

(b) **leave-one-family-out (OOD)** — the load-bearing regime: the probe is trained on all task
    families but one and evaluated on the held-out family, rotated over every family. A probe that
    found a dataset-specific shortcut collapses here; a probe that reads a geometric quantity
    transfers. README Evaluation (c).

Both return sorted integer index arrays so a downstream fit is deterministic in row order.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def in_distribution_split(
    n: int, test_fraction: float, seed: int
) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    """Seeded random train/test split over ``n`` items (same-family held-out prompts).

    Args:
        n: number of items.
        test_fraction: fraction assigned to the held-out (test) split, in (0, 1).
        seed: seed for the permutation — the only source of randomness; fixed seed => fixed split.

    Returns:
        ``(train_idx, test_idx)`` — disjoint, sorted, covering ``range(n)``.
    """
    if not 0.0 < test_fraction < 1.0:
        raise ValueError(f"test_fraction must be in (0, 1); got {test_fraction}")
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    n_test = int(round(n * test_fraction))
    if not 0 < n_test < n:
        raise ValueError(f"test_fraction {test_fraction} yields {n_test} test items for n={n}")
    test_idx = np.sort(perm[:n_test])
    train_idx = np.sort(perm[n_test:])
    return train_idx, test_idx


def leave_one_family_out(
    family_labels: ArrayLike,
) -> list[tuple[object, NDArray[np.intp], NDArray[np.intp]]]:
    """Leave-one-family-out rotation over the distinct family labels.

    Args:
        family_labels: length-N array of a family label per item.

    Returns:
        One tuple per distinct family (in sorted label order): ``(held_out_family, train_idx,
        test_idx)`` where ``test_idx`` are that family's items and ``train_idx`` are all the rest.
    """
    fam = np.asarray(family_labels)
    if fam.ndim != 1:
        raise ValueError(f"family_labels must be 1-D; got shape {fam.shape}")
    rotations: list[tuple[object, NDArray[np.intp], NDArray[np.intp]]] = []
    for f in np.unique(fam):
        test_idx = np.sort(np.flatnonzero(fam == f))
        train_idx = np.sort(np.flatnonzero(fam != f))
        if train_idx.size == 0:
            raise ValueError(f"holding out family {f!r} leaves no training data")
        rotations.append((f.item() if hasattr(f, "item") else f, train_idx, test_idx))
    return rotations
