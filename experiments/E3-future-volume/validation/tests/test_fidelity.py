"""fidelity.py — two-part target and within-family fidelity on planted fixtures (redesign B, C).

Every answer is planted by construction (see `_fixtures`):
  * degenerate-floor items sit on ``N*log(epsilon)`` and are split out; the degeneracy classifier
    separates them; continuous R²/Spearman are computed on the non-degenerate subset only (B);
  * within-family metrics recover a genuine within-family signal (make_linear_signal) and reject a
    family-band-only fixture with no within-family signal (make_family_band_only) (C);
  * the family-mean oracle is beaten by a real probe and matched by a family-band-only one;
  * the length gate collapses a probe that reads verbosity (make_length_confound).
"""

from __future__ import annotations

import math

import numpy as np

from e3_validation.fidelity import (
    continuous_fidelity,
    degeneracy_auroc,
    degenerate_floor,
    degenerate_mask,
    family_mean_oracle_r2,
    length_residualized_within_family_spearman,
    within_family_metrics,
)
from e3_validation.probe import ridge_probe
from e3_validation.splits import in_distribution_split
from e3_validation.volume import EPSILON

from ._fixtures import (
    PASSING_THRESHOLDS as T,
)
from ._fixtures import (
    make_degenerate_mixed,
    make_family_band_only,
    make_length_confound,
    make_linear_signal,
)


# ---- B: degenerate floor split + degeneracy classifier + non-degenerate continuous fidelity ----
def test_degenerate_floor_value_is_exact():
    # N=10 -> 10*log(1e-6) = -138.15510557964274, the fixture-D minimum.
    assert math.isclose(degenerate_floor(10, EPSILON), 10.0 * math.log(EPSILON), rel_tol=0, abs_tol=0)


def test_degenerate_mask_recovers_floor_items():
    _X, y, is_deg = make_degenerate_mixed()
    mask = degenerate_mask(y, n_continuations=10, epsilon=EPSILON)
    assert np.array_equal(mask, is_deg)  # floor items recovered exactly


def test_degeneracy_classifier_separates_the_floor():
    X, _y, is_deg = make_degenerate_mixed()
    tr, te = in_distribution_split(len(is_deg), 0.30, seed=1)
    auc = degeneracy_auroc(X[tr], is_deg[tr], X[te], is_deg[te])
    assert auc > 0.90  # the hidden state encodes whether the prompt is on the degenerate floor


def test_continuous_fidelity_on_nondegenerate_subset():
    X, y, is_deg = make_degenerate_mixed()
    tr, te = in_distribution_split(len(y), 0.30, seed=1)
    res = ridge_probe(X[tr], y[tr], X[te], y[te])
    nondeg = ~degenerate_mask(y[te], n_continuations=10, epsilon=EPSILON)
    r2, sp, n_nd = continuous_fidelity(res.predictions, y[te], nondeg)
    assert n_nd == int(nondeg.sum()) and n_nd < len(te)  # the mass point was split out
    assert r2 > 0.50 and sp > 0.50  # continuous read is real on the non-degenerate items


# ---- C: within-family metrics and the family-mean-oracle margin ----
def test_within_family_signal_recovered_when_present():
    X, y, fam = make_linear_signal()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    res = ridge_probe(X[tr], y[tr], X[te], y[te])
    _wf_r2, wf_sp = within_family_metrics(res.predictions, y[te], y[tr], fam[te], fam[tr])
    assert wf_sp > T.within_family_spearman_min  # genuine within-family signal


def test_within_family_signal_absent_for_family_band_only():
    X, y, fam = make_family_band_only()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    res = ridge_probe(X[tr], y[tr], X[te], y[te])
    _wf_r2, wf_sp = within_family_metrics(res.predictions, y[te], y[tr], fam[te], fam[tr])
    # heterogeneous family MEANS but no within-family signal -> within-family Spearman collapses.
    assert wf_sp < T.within_family_spearman_min


def test_family_oracle_beaten_by_real_probe_matched_by_band_only():
    # real within-family signal: probe beats the family-mean oracle by a clear margin.
    Xs, ys, fs = make_linear_signal()
    trs, tes = in_distribution_split(len(ys), 0.25, seed=1)
    rs = ridge_probe(Xs[trs], ys[trs], Xs[tes], ys[tes])
    oracle_s = family_mean_oracle_r2(ys[trs], ys[tes], fs[trs], fs[tes])
    assert rs.r2 - oracle_s > T.family_oracle_margin_min

    # family-band-only: the probe cannot beat predict-by-family-mean.
    Xb, yb, fb = make_family_band_only()
    trb, teb = in_distribution_split(len(yb), 0.25, seed=1)
    rb = ridge_probe(Xb[trb], yb[trb], Xb[teb], yb[teb])
    oracle_b = family_mean_oracle_r2(yb[trb], yb[teb], fb[trb], fb[teb])
    assert rb.r2 - oracle_b < T.family_oracle_margin_min


# ---- F: the length gate ----
def test_length_gate_collapses_a_verbosity_readout():
    X, y, fam, lengths = make_length_confound()
    tr, te = in_distribution_split(len(y), 0.25, seed=1)
    res = ridge_probe(X[tr], y[tr], X[te], y[te])

    # Before length control the within-family Spearman is high (probe reads length, which tracks vol).
    _wf_r2, wf_sp = within_family_metrics(res.predictions, y[te], y[tr], fam[te], fam[tr])
    assert wf_sp > T.within_family_spearman_min

    # After residualizing volume on length, the within-family signal collapses.
    len_resid_sp = length_residualized_within_family_spearman(
        res.predictions, y[te], y[tr], fam[te], fam[tr], lengths[tr], lengths[te]
    )
    assert len_resid_sp < T.within_family_spearman_min
