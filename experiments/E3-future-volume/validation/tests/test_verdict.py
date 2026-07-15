"""verdict.py — the pre-registered branch logic on planted metric tuples (E3 README § Verdict).

Each of the five branches is exercised directly with constructed VerdictInputs, plus the boundary
behavior: the thresholds are strict/inclusive exactly as documented, and the branch that a fixture
class alone cannot reach in the pipeline suite (refuted/no-margin-over-verbalized) is covered here.
The verdict code invents no threshold; every number below is supplied by the test.
"""

from __future__ import annotations

from dataclasses import replace

from e3_validation.verdict import (
    Verdict,
    VerdictInputs,
    VerdictThresholds,
    decide,
    has_continuous_fidelity,
)

from ._fixtures import PASSING_THRESHOLDS as T


def _inputs(**kw) -> VerdictInputs:
    base = dict(
        r2_indist=0.90,
        r2_classmean_indist=0.40,
        r2_ood=0.80,
        auc_binary=0.95,
        probe_vs_vc_ci_low=0.10,
    )
    base.update(kw)
    return VerdictInputs(**base)


def test_confirmed_shaped():
    # fidelity + OOD transfer + beats VC (CI low > 0).
    assert decide(_inputs(), T) is Verdict.CONFIRMED_SHAPED


def test_no_signal():
    # no fidelity (low R^2) and binarized AUROC below its bar.
    assert decide(_inputs(r2_indist=0.02, r2_classmean_indist=0.0, auc_binary=0.52), T) is (
        Verdict.REFUTED_NO_SIGNAL
    )


def test_binary_only():
    # R^2 clears the fidelity bar but not the class-mean margin; binarized AUROC clears its bar.
    v = decide(_inputs(r2_indist=0.65, r2_classmean_indist=0.63, auc_binary=0.95), T)
    assert v is Verdict.REFUTED_BINARY_ONLY


def test_ood_failure():
    # fidelity present in-distribution, OOD below the bar.
    assert decide(_inputs(r2_ood=0.10), T) is Verdict.REFUTED_OOD_FAILURE


def test_no_margin_over_verbalized():
    # fidelity + OOD transfer, but the probe does not beat verbalized confidence (CI low <= floor).
    assert decide(_inputs(probe_vs_vc_ci_low=-0.02), T) is (
        Verdict.REFUTED_NO_MARGIN_OVER_VERBALIZED
    )


def test_vc_ci_low_exactly_at_floor_does_not_beat():
    # beats-VC requires ci_low STRICTLY above the floor; equality is not a win.
    assert decide(_inputs(probe_vs_vc_ci_low=0.0), T) is (
        Verdict.REFUTED_NO_MARGIN_OVER_VERBALIZED
    )


def test_fidelity_r2_bar_is_inclusive():
    # r2_indist exactly at r2_fidelity_min counts as clearing the bar (>=). class-mean 0 so the
    # margin clause is satisfied cleanly and does not confound the R^2-bar boundary.
    t = VerdictThresholds(
        r2_fidelity_min=0.50,
        r2_margin_over_classmean_min=0.10,
        r2_ood_min=0.50,
        auc_binary_min=0.70,
    )
    assert has_continuous_fidelity(_inputs(r2_indist=0.50, r2_classmean_indist=0.0), t)
    assert not has_continuous_fidelity(_inputs(r2_indist=0.49, r2_classmean_indist=0.0), t)


def test_fidelity_classmean_margin_bar_is_inclusive():
    # margin (r2_indist - r2_classmean) exactly at its minimum counts (>=). class-mean 0 keeps the
    # subtraction exact in floating point (x - 0.0 == x).
    t = VerdictThresholds(
        r2_fidelity_min=0.0,
        r2_margin_over_classmean_min=0.10,
        r2_ood_min=0.50,
        auc_binary_min=0.70,
    )
    assert has_continuous_fidelity(_inputs(r2_indist=0.10, r2_classmean_indist=0.0), t)
    assert not has_continuous_fidelity(_inputs(r2_indist=0.09, r2_classmean_indist=0.0), t)


def test_auc_binary_bar_is_inclusive():
    # binarized AUROC exactly at the bar counts as "binary signal exists".
    no_fidelity = _inputs(r2_indist=0.0, r2_classmean_indist=0.0)
    at_bar = replace(T, auc_binary_min=0.70)
    assert decide(replace_auc(no_fidelity, 0.70), at_bar) is Verdict.REFUTED_BINARY_ONLY
    assert decide(replace_auc(no_fidelity, 0.699), at_bar) is Verdict.REFUTED_NO_SIGNAL


def replace_auc(inp: VerdictInputs, auc: float) -> VerdictInputs:
    return VerdictInputs(
        r2_indist=inp.r2_indist,
        r2_classmean_indist=inp.r2_classmean_indist,
        r2_ood=inp.r2_ood,
        auc_binary=auc,
        probe_vs_vc_ci_low=inp.probe_vs_vc_ci_low,
    )
