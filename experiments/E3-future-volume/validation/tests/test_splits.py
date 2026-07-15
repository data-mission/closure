"""splits.py — the two evaluation regimes (e3-0001).

The in-distribution split is a disjoint, covering, seed-determined partition; leave-one-family-out
holds out exactly one family per rotation and trains on all the rest.
"""

from __future__ import annotations

import numpy as np
import pytest

from e3_validation.splits import in_distribution_split, leave_one_family_out


def test_in_distribution_split_is_disjoint_and_covering():
    train, test = in_distribution_split(100, test_fraction=0.25, seed=42)
    assert len(test) == 25
    assert len(train) == 75
    assert set(train).isdisjoint(set(test))
    assert sorted(np.concatenate([train, test])) == list(range(100))
    # sorted index arrays -> deterministic downstream row order
    assert list(train) == sorted(train)
    assert list(test) == sorted(test)


def test_in_distribution_split_is_seed_deterministic():
    a = in_distribution_split(100, 0.25, seed=1)
    b = in_distribution_split(100, 0.25, seed=1)
    c = in_distribution_split(100, 0.25, seed=2)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert not np.array_equal(a[1], c[1])  # different seed -> different split


def test_in_distribution_split_rejects_degenerate_fraction():
    with pytest.raises(ValueError):
        in_distribution_split(100, test_fraction=0.0, seed=1)
    with pytest.raises(ValueError):
        in_distribution_split(4, test_fraction=0.001, seed=1)  # rounds to 0 test items


def test_leave_one_family_out_holds_out_each_family_once():
    fam = np.array([0, 0, 1, 1, 2, 2, 2])
    rotations = leave_one_family_out(fam)
    assert [f for f, _, _ in rotations] == [0, 1, 2]
    for held, train_idx, test_idx in rotations:
        assert set(fam[test_idx]) == {held}
        assert held not in set(fam[train_idx])
        assert set(train_idx).isdisjoint(set(test_idx))
        assert sorted(np.concatenate([train_idx, test_idx])) == list(range(len(fam)))
