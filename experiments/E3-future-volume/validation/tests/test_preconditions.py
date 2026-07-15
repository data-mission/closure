"""preconditions.py — the min-negatives guard and per-family exclusion accounting (redesign A).

The rehearsal fired the strongest verdict off ONE negative in 41 items. These tests plant the
rehearsal shape directly and assert the guard routes it to the honest terminal state, and that the
guard boundary is inclusive. Exclusion accounting is checked against hand-counted masks.
"""

from __future__ import annotations

import pytest

from e3_validation.preconditions import correctness_arm_evaluable, exclusion_report
from e3_validation.verdict import Verdict, decide

from ._fixtures import PASSING_THRESHOLDS as T
from ._fixtures import passing_inputs


def test_rehearsal_shape_one_negative_is_not_evaluable():
    # 1 negative, min 20: the correctness arm cannot be evaluated -> terminal honest state.
    assert not correctness_arm_evaluable(1, T.min_negatives)
    assert decide(passing_inputs(n_negatives=1), T) is Verdict.NOT_EVALUABLE_CORRECTNESS_ARM


def test_evaluable_boundary_is_inclusive():
    assert correctness_arm_evaluable(20, 20)
    assert not correctness_arm_evaluable(19, 20)


def test_min_negatives_must_be_nonnegative():
    with pytest.raises(ValueError):
        correctness_arm_evaluable(5, -1)


def test_exclusion_report_counts_per_family():
    fams = ["arithmetic", "arithmetic", "factual", "factual", "deduction"]
    # exclude one arithmetic (sampling failed) and the deduction item (gold null).
    excluded = [True, False, False, False, True]
    rep = exclusion_report(fams, excluded)
    assert rep.per_family_excluded == {"arithmetic": 1, "deduction": 1, "factual": 0}
    assert rep.per_family_answerable == {"arithmetic": 1, "deduction": 0, "factual": 2}
    assert rep.total_excluded == 2
    assert rep.total_answerable == 3


def test_exclusion_report_length_mismatch_fails_closed():
    with pytest.raises(ValueError):
        exclusion_report(["a", "b"], [True])
