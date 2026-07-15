"""verdict.py — the redesigned pre-registered branch logic on planted metric tuples.

Each branch of the audit-driven redesign is exercised directly with constructed ``VerdictInputs`` via
the ``passing_inputs`` helper (a fully gate-satisfying tuple) with a single failing metric planted to
reach a target branch. Boundary behaviour (inclusive ``>=`` bars, strict added-value floors) and the
two load-bearing precedences (precondition BEFORE any branch; OOD BEFORE the verbalized/added-value
gates) are covered. The verdict code invents no threshold; every number below is supplied by the test.

Contract change from the pre-redesign suite (documented in VALIDATION.md): ``VerdictInputs`` and
``VerdictThresholds`` gained the precondition, two-part-fidelity, within-family, length, OOD-Spearman,
and B3/B4 fields; ``r2_ood`` / ``r2_ood_min`` were replaced by the within-family OOD Spearman fields;
and the old ``refuted/no-signal`` misnaming of an above-floor-R² margin failure is now
``REFUTED_MARGIN_ONLY``. The old five-field tuples embody that superseded contract and are replaced.
"""

from __future__ import annotations

from dataclasses import replace

from e3_validation.verdict import (
    Verdict,
    VerdictThresholds,
    decide,
    has_continuous_fidelity,
)

from ._fixtures import PASSING_THRESHOLDS as T
from ._fixtures import passing_inputs


# ------------------------------------------------------------------------------------------------
# Precondition layer (A) — checked before any branch.
# ------------------------------------------------------------------------------------------------
def test_not_evaluable_when_negatives_below_min():
    # rehearsal-shaped: everything else passes, but only 1 negative -> NOT_EVALUABLE, not confirmed.
    assert decide(passing_inputs(n_negatives=1), T) is Verdict.NOT_EVALUABLE_CORRECTNESS_ARM


def test_precondition_dominates_every_other_failure():
    # even with fidelity/OOD/added-value ALSO failing, too-few-negatives is the terminal honest state.
    inp = passing_inputs(
        n_negatives=0,
        r2_nondegenerate=0.0,
        within_family_spearman=0.0,
        ood_pooled_spearman=0.0,
        probe_vs_vc_ci_low=-1.0,
    )
    assert decide(inp, T) is Verdict.NOT_EVALUABLE_CORRECTNESS_ARM


def test_precondition_boundary_is_inclusive():
    # exactly min_negatives is evaluable (>=); one below is not.
    assert decide(passing_inputs(n_negatives=T.min_negatives), T) is Verdict.CONFIRMED_SHAPED
    assert decide(passing_inputs(n_negatives=T.min_negatives - 1), T) is (
        Verdict.NOT_EVALUABLE_CORRECTNESS_ARM
    )


# ------------------------------------------------------------------------------------------------
# Confirmed.
# ------------------------------------------------------------------------------------------------
def test_confirmed_shaped():
    assert decide(passing_inputs(), T) is Verdict.CONFIRMED_SHAPED


# ------------------------------------------------------------------------------------------------
# Fidelity present but a robustness / added-value gate fails.
# ------------------------------------------------------------------------------------------------
def test_length_confounded():
    # within-family fidelity holds, but not after residualizing volume on length.
    assert decide(passing_inputs(within_family_spearman_length_resid=0.10), T) is (
        Verdict.REFUTED_LENGTH_CONFOUNDED
    )


def test_ood_range_uncovered():
    assert decide(passing_inputs(ood_range_uncovered=True), T) is (
        Verdict.REFUTED_OOD_RANGE_UNCOVERED
    )


def test_ood_failure_on_pooled():
    assert decide(passing_inputs(ood_pooled_spearman=0.10), T) is Verdict.REFUTED_OOD_FAILURE


def test_ood_failure_on_single_rotation_floor():
    # pooled clears but one rotation collapses below the per-family floor.
    assert decide(passing_inputs(ood_min_rotation_spearman=0.10), T) is (
        Verdict.REFUTED_OOD_FAILURE
    )


def test_no_margin_over_verbalized():
    assert decide(passing_inputs(probe_vs_vc_ci_low=-0.02), T) is (
        Verdict.REFUTED_NO_MARGIN_OVER_VERBALIZED
    )


def test_no_margin_over_entropy():
    assert decide(passing_inputs(probe_vs_b3_ci_low=-0.02), T) is (
        Verdict.REFUTED_NO_MARGIN_OVER_ENTROPY
    )


def test_dominated_by_correctness_probe():
    # B4 significantly beats the probe (CI-low of B4-minus-probe above the ceiling).
    assert decide(passing_inputs(b4_vs_probe_ci_low=0.05), T) is (
        Verdict.REFUTED_DOMINATED_BY_CORRECTNESS_PROBE
    )


# ------------------------------------------------------------------------------------------------
# No continuous fidelity.
# ------------------------------------------------------------------------------------------------
def test_binary_only():
    # fidelity denied (within-family fails) but a binarized signal clears its bar.
    inp = passing_inputs(within_family_spearman=0.0, family_oracle_margin=0.0, auc_binary=0.95)
    assert decide(inp, T) is Verdict.REFUTED_BINARY_ONLY


def test_margin_only_not_no_signal():
    # THE FIX: above-floor R^2 that fails the margin/within-family gates, with NO binarized signal,
    # is refuted/margin-only — the pre-redesign code mislabeled this row refuted/no-signal.
    inp = passing_inputs(
        r2_nondegenerate=0.80,  # clears the fidelity floor
        within_family_spearman=0.0,  # but within-family fidelity denied
        family_oracle_margin=0.0,
        auc_binary=0.55,  # and no binarized signal
    )
    assert decide(inp, T) is Verdict.REFUTED_MARGIN_ONLY


def test_no_signal():
    # R^2 below the floor AND no binarized signal.
    inp = passing_inputs(
        r2_nondegenerate=0.05,
        spearman_nondegenerate=0.05,
        within_family_spearman=0.0,
        family_oracle_margin=0.0,
        auc_binary=0.52,
    )
    assert decide(inp, T) is Verdict.REFUTED_NO_SIGNAL


# ------------------------------------------------------------------------------------------------
# Precedence.
# ------------------------------------------------------------------------------------------------
def test_ood_resolved_before_verbalized_gate():
    # OOD collapse AND a failing verbalized margin -> OOD wins (documented OOD-before-VC precedence).
    inp = passing_inputs(ood_pooled_spearman=0.10, probe_vs_vc_ci_low=-1.0)
    assert decide(inp, T) is Verdict.REFUTED_OOD_FAILURE


def test_length_resolved_before_ood():
    # length gate sits with fidelity, ahead of OOD.
    inp = passing_inputs(within_family_spearman_length_resid=0.0, ood_pooled_spearman=0.0)
    assert decide(inp, T) is Verdict.REFUTED_LENGTH_CONFOUNDED


# ------------------------------------------------------------------------------------------------
# Boundaries — bars inclusive, added-value floors strict.
# ------------------------------------------------------------------------------------------------
def test_fidelity_bars_are_inclusive():
    t = replace(T, r2_fidelity_min=0.50, spearman_fidelity_min=0.50)
    assert has_continuous_fidelity(passing_inputs(r2_nondegenerate=0.50), t)
    assert not has_continuous_fidelity(passing_inputs(r2_nondegenerate=0.49), t)
    assert has_continuous_fidelity(passing_inputs(spearman_nondegenerate=0.50), t)
    assert not has_continuous_fidelity(passing_inputs(spearman_nondegenerate=0.49), t)


def test_within_family_and_oracle_margin_bars_are_inclusive():
    t = replace(T, within_family_spearman_min=0.50, family_oracle_margin_min=0.10)
    assert has_continuous_fidelity(passing_inputs(within_family_spearman=0.50), t)
    assert not has_continuous_fidelity(passing_inputs(within_family_spearman=0.49), t)
    assert has_continuous_fidelity(passing_inputs(family_oracle_margin=0.10), t)
    assert not has_continuous_fidelity(passing_inputs(family_oracle_margin=0.09), t)


def test_added_value_floors_are_strict():
    # equality at the floor is NOT a beat (probe must strictly exceed).
    assert decide(passing_inputs(probe_vs_vc_ci_low=0.0), T) is (
        Verdict.REFUTED_NO_MARGIN_OVER_VERBALIZED
    )
    assert decide(passing_inputs(probe_vs_b3_ci_low=0.0), T) is (
        Verdict.REFUTED_NO_MARGIN_OVER_ENTROPY
    )
    # B4 exactly at the ceiling does NOT count as dominating (<= ceiling is fine).
    assert decide(passing_inputs(b4_vs_probe_ci_low=0.0), T) is Verdict.CONFIRMED_SHAPED


def test_auc_binary_bar_is_inclusive():
    no_fid = dict(within_family_spearman=0.0, family_oracle_margin=0.0, r2_nondegenerate=0.05,
                  spearman_nondegenerate=0.05)
    at_bar = replace(T, auc_binary_min=0.70)
    assert decide(passing_inputs(auc_binary=0.70, **no_fid), at_bar) is Verdict.REFUTED_BINARY_ONLY
    assert decide(passing_inputs(auc_binary=0.699, **no_fid), at_bar) is Verdict.REFUTED_NO_SIGNAL
