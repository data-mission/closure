"""correctness.py — frozen orientation, out-of-fold scoring, missing-VC rule (redesign E).

Planted answers (see `_fixtures.make_correctness_arms`): the volume probe and B3 entropy separate
correctness strongly; B4 (correctness probe) is comparable but does not significantly beat the probe;
verbalized confidence is weak and near-constant with some missing values. These tests assert the
frozen orientation table, that probe/B4 scores are out-of-fold and deterministic, and that the
added-value comparisons come out with the planted signs (probe beats VC on the VC-present subset and
beats B3 on the full subset; B4 does not significantly beat the probe).
"""

from __future__ import annotations

import numpy as np

from e3_validation.compare import paired_bootstrap_auroc_diff
from e3_validation.correctness import (
    ORIENTATION,
    ArmAurocs,
    arm_aurocs,
    b3_scores,
    b4_scores_oof,
    probe_scores_oof,
    vc_present_mask,
    verbalized_scores,
)

from ._fixtures import make_correctness_arms


def test_orientation_table_is_frozen():
    assert ORIENTATION == {
        "probe": "-predicted_volume",
        "b3": "-entropy",
        "b4": "P(correct)",
        "verbalized": "stated_value",
    }


def test_probe_scores_are_out_of_fold_and_deterministic():
    d = make_correctness_arms()
    a = probe_scores_oof(d["X"], d["volume"], k=5, seed=13)
    b = probe_scores_oof(d["X"], d["volume"], k=5, seed=13)
    assert a.shape == d["volume"].shape
    assert np.array_equal(a, b)  # seeded k-fold -> identical out-of-fold scores


def test_b4_scores_are_probabilities_and_deterministic():
    d = make_correctness_arms()
    a = b4_scores_oof(d["X"], d["correctness"], k=5, seed=13)
    b = b4_scores_oof(d["X"], d["correctness"], k=5, seed=13)
    assert np.all((a >= 0.0) & (a <= 1.0))  # P(correct)
    assert np.array_equal(a, b)


def test_b3_orientation_is_negated_entropy():
    d = make_correctness_arms()
    assert np.array_equal(b3_scores(d["entropy"]), -d["entropy"])


def test_verbalized_missing_carried_as_nan_and_masked():
    d = make_correctness_arms()
    vc = verbalized_scores(d["vc"])
    present = vc_present_mask(vc)
    assert present.sum() == np.sum(~np.isnan(d["vc"]))
    assert present.sum() < len(vc)  # some are missing by construction


def test_arm_aurocs_reports_both_subsets():
    d = make_correctness_arms()
    probe = probe_scores_oof(d["X"], d["volume"], k=5, seed=13)
    present = vc_present_mask(verbalized_scores(d["vc"]))
    res = arm_aurocs(probe, d["correctness"], present)
    assert isinstance(res, ArmAurocs)
    assert 0.5 < res.full <= 1.0 and 0.5 < res.vc_present <= 1.0


def test_probe_beats_verbalized_on_vc_present_subset():
    d = make_correctness_arms()
    probe = probe_scores_oof(d["X"], d["volume"], k=5, seed=13)
    vc = verbalized_scores(d["vc"])
    present = vc_present_mask(vc)
    res = paired_bootstrap_auroc_diff(
        probe[present], vc[present], d["correctness"][present], n_boot=2000, ci_level=0.95, seed=2
    )
    assert res.ci_low > 0.0  # probe strictly beats verbalized on the shared VC-present items


def test_probe_beats_entropy_on_full_subset():
    d = make_correctness_arms()
    probe = probe_scores_oof(d["X"], d["volume"], k=5, seed=13)
    b3 = b3_scores(d["entropy"])
    res = paired_bootstrap_auroc_diff(
        probe, b3, d["correctness"], n_boot=2000, ci_level=0.95, seed=2
    )
    assert res.ci_low > 0.0


def test_b4_does_not_significantly_beat_probe():
    d = make_correctness_arms()
    probe = probe_scores_oof(d["X"], d["volume"], k=5, seed=13)
    b4 = b4_scores_oof(d["X"], d["correctness"], k=5, seed=13)
    res = paired_bootstrap_auroc_diff(
        b4, probe, d["correctness"], n_boot=2000, ci_level=0.95, seed=2
    )
    assert res.ci_low <= 0.0  # (B4 - probe) CI-low does not exclude zero on the positive side
