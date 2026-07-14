"""Detector fixtures (0007 contamination rule) with planted contaminated + clean claims.

The detector must flag EXACTLY the planted contaminated set across the full pre-registered
sensitivity sweep {0.65, 0.70, 0.75} x {0.05, 0.10, 0.15}. Grounding values are planted via
the stub scalar so the cases are hand-computable.
"""

from __future__ import annotations

import itertools

import pytest

from closure_harness.config import CONFIG
from closure_harness.detector import is_contaminated
from closure_harness.schema import Claim

SWEEP = list(
    itertools.product(
        CONFIG.detector.grounding_floor_sweep, CONFIG.detector.drop_ceiling_sweep
    )
)

# Two sources; each planted claim cites source index 0.
SOURCES = ["source-zero", "source-one"]


def _planted(stub_scalar):
    """A contaminated claim and a clean claim, with grounding planted at both source states.

    contaminated: without=0.90 (>= every sweep floor), full=0.92 (drop 0.02 < every ceiling).
    clean:        without=0.20 (< every sweep floor), full=0.90 (drop 0.70, collapses).
    A boundary-clean claim tests the strict-inequality edges: without exactly at 0.75 but drop
    exactly 0.15 (not < 0.15 at the tightest ceiling) — must stay unflagged there.
    """
    contaminated = Claim(id=1, text="contaminated-claim", source_ids=(0,))
    clean = Claim(id=2, text="clean-claim", source_ids=(0,))

    s = stub_scalar()
    # full sources present
    s.set(SOURCES, contaminated.text, 0.92)
    s.set(SOURCES, clean.text, 0.90)
    # source 0 removed -> only source-one remains
    s.set(["source-one"], contaminated.text, 0.90)
    s.set(["source-one"], clean.text, 0.20)
    return s, contaminated, clean


@pytest.mark.parametrize("floor,ceiling", SWEEP)
def test_flags_exactly_planted_set(stub_scalar, floor, ceiling):
    s, contaminated, clean = _planted(stub_scalar)
    assert is_contaminated(s, SOURCES, contaminated, grounding_floor=floor, drop_ceiling=ceiling) is True
    assert is_contaminated(s, SOURCES, clean, grounding_floor=floor, drop_ceiling=ceiling) is False


def test_decorative_claim_never_contaminated(stub_scalar):
    # No source_ids to remove -> the contamination test does not apply (contraction's
    # decorative rule handles it instead).
    s = stub_scalar(default=1.0)
    decorative = Claim(id=3, text="decorative", source_ids=())
    for floor, ceiling in SWEEP:
        assert is_contaminated(s, SOURCES, decorative, grounding_floor=floor, drop_ceiling=ceiling) is False


def test_boundary_floor_and_ceiling_are_strict(stub_scalar):
    # without == floor passes (>=), drop == ceiling fails (< is strict).
    claim = Claim(id=1, text="edge", source_ids=(0,))
    s = stub_scalar()
    s.set(["source-one"], claim.text, 0.70)  # without exactly at 0.70 floor
    s.set(SOURCES, claim.text, 0.80)  # drop = 0.10 exactly at 0.10 ceiling
    # floor satisfied (0.70 >= 0.70) but drop NOT < 0.10 -> not contaminated
    assert is_contaminated(s, SOURCES, claim, grounding_floor=0.70, drop_ceiling=0.10) is False
    # loosen ceiling to 0.15: now drop 0.10 < 0.15 and floor holds -> contaminated
    assert is_contaminated(s, SOURCES, claim, grounding_floor=0.70, drop_ceiling=0.15) is True


def test_frozen_defaults_match_center_of_sweep(stub_scalar):
    s, contaminated, clean = _planted(stub_scalar)
    # No overrides -> uses CONFIG.detector (0.7 / 0.10), the sweep centre.
    assert is_contaminated(s, SOURCES, contaminated) is True
    assert is_contaminated(s, SOURCES, clean) is False


def test_out_of_range_source_ids_raise(stub_scalar):
    # A hallucinated citation index would remove nothing, force drop == 0, and mislabel
    # the claim contaminated regardless of its real grounding. Fail loudly instead; the
    # output goes to the pre-registered exclusion bucket.
    s = stub_scalar(default=0.9)
    bogus = Claim(id=1, text="bogus-ref", source_ids=(5,))
    with pytest.raises(ValueError, match="out of range"):
        is_contaminated(s, SOURCES, bogus)
    negative = Claim(id=2, text="neg-ref", source_ids=(-1,))
    with pytest.raises(ValueError, match="out of range"):
        is_contaminated(s, SOURCES, negative)


def test_boundary_robust_to_float_noise(stub_scalar):
    # 0.30 - 0.20 = 0.0999...8 in float64: a drop that is mathematically exactly at the
    # 0.10 ceiling must still be excluded (strict <), not flip to contaminated via
    # subtraction noise. Quantization (config.quantize_decimals) makes the boundary exact.
    claim = Claim(id=1, text="float-edge", source_ids=(0,))
    s = stub_scalar()
    s.set(["source-one"], claim.text, 0.20)
    s.set(SOURCES, claim.text, 0.30)  # drop = 0.30 - 0.20 == 0.10 exactly (mathematically)
    assert is_contaminated(s, SOURCES, claim, grounding_floor=0.15, drop_ceiling=0.10) is False
