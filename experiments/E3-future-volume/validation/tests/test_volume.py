"""Fixture D — the semantic-volume statistic on hand-computed cases (e3-0002).

Every value here is derivable on paper from ``log det(G + epsilon I)`` over the mean-centered,
L2-normalized embeddings, and asserted to numerical tolerance:

- N identical vectors -> centered Gram is the zero matrix -> logdet = N * log(epsilon) exactly.
- The N standard-basis vectors -> the centered-normalized Gram has eigenvalues {0, N/(N-1) (x N-1)},
  so logdet = log(epsilon) + (N-1) * log(N/(N-1) + epsilon).
- Volume is strictly monotone in a planted dispersion parameter.
- The result is finite and stable across a range of epsilon around the registered 1e-6.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from e3_validation.volume import EPSILON, semantic_volume

from ._fixtures import dispersion_family


def test_identical_vectors_hit_degenerate_minimum():
    # All N continuations identical -> every mean-centered vector is zero -> Gram is the zero
    # matrix -> det(0 + eps I) = eps^N -> logdet = N * log(eps), EXACTLY.
    for n in (2, 5, 10):
        x = np.tile(np.array([1.0, 2.0, -3.0, 0.5, 7.0]), (n, 1))
        expected = n * math.log(EPSILON)
        assert math.isclose(semantic_volume(x), expected, rel_tol=0.0, abs_tol=1e-9)


def test_orthonormal_basis_matches_closed_form():
    # x = I_N. After centering and normalizing, G = (N/(N-1)) I - (1/(N-1)) J, whose eigenvalues are
    # 0 (the all-ones direction, killed by centering) and N/(N-1) with multiplicity N-1.
    # logdet(G + eps I) = log(eps) + (N-1) * log(N/(N-1) + eps).
    for n in (3, 4, 5, 6):
        x = np.eye(n)
        expected = math.log(EPSILON) + (n - 1) * math.log(n / (n - 1) + EPSILON)
        assert math.isclose(semantic_volume(x), expected, rel_tol=0.0, abs_tol=1e-8)


def test_two_opposite_vectors_hand_value():
    # v1 = e, v2 = -e. Centered = v1, v2 (mean 0); normalized -> e, -e. G = [[1,-1],[-1,1]].
    # det(G + eps I) = (1+eps)^2 - 1 = 2 eps + eps^2.
    x = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    expected = math.log(2 * EPSILON + EPSILON**2)
    assert math.isclose(semantic_volume(x), expected, rel_tol=0.0, abs_tol=1e-9)


def test_volume_strictly_increasing_in_dispersion():
    # Planted monotonicity: more orthogonal spread -> strictly larger volume.
    svals = np.linspace(0.05, 1.5, 12)
    vols = np.array([semantic_volume(dispersion_family(s)) for s in svals])
    diffs = np.diff(vols)
    assert np.all(diffs > 0.0), f"not strictly increasing: {vols}"


def test_epsilon_stability_finite_and_ordered():
    # For the registered epsilon and neighbours, the volume is finite; and because a smaller ridge
    # floors the near-degenerate directions lower, the volume decreases as epsilon shrinks.
    x = dispersion_family(0.8)
    v_registered = semantic_volume(x, epsilon=EPSILON)
    assert math.isfinite(v_registered)
    v_big = semantic_volume(x, epsilon=1e-4)
    v_small = semantic_volume(x, epsilon=1e-8)
    assert v_small < v_registered < v_big  # monotone in epsilon, all finite


def test_raw_centered_gram_would_be_negative_infinite_without_ridge():
    # The reason the epsilon ridge exists: centering drops the Gram rank by one, so the un-ridged
    # centered Gram is singular. With epsilon = 0 the determinant is exactly 0 and logdet = -inf.
    x = np.eye(4)
    v0 = semantic_volume(x, epsilon=0.0)
    assert v0 == -math.inf


def test_rejects_non_2d_input():
    with pytest.raises(ValueError):
        semantic_volume(np.zeros((3, 4, 5)))
