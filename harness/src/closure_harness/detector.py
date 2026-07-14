"""Contamination detector (decision 0007).

A claim is contaminated iff, with ALL of its own source_ids removed, its grounding stays
>= grounding_floor (default 0.7) AND grounding_drop < drop_ceiling (default 0.10) — i.e. it
was reproduced from parametric memory, not the provided sources.

This module drives Arm C's contraction ONLY (contraction.py). It is never imported by
outcomes.py; an import-hygiene test enforces that separation (0007: no arm is scored by the
instrument that built it).
"""

from __future__ import annotations

from typing import Sequence

from .config import CONFIG, DetectorConfig
from .grounding import grounding, grounding_without
from .nli import Scalar
from .schema import Claim


def is_contaminated(
    scalar: Scalar,
    sources: Sequence[str],
    claim: Claim,
    config: DetectorConfig = CONFIG.detector,
    grounding_floor: float | None = None,
    drop_ceiling: float | None = None,
) -> bool:
    """0007 contamination rule for a single claim.

    grounding_floor / drop_ceiling override the frozen point for the pre-registered
    sensitivity sweep; unset, they use the frozen values.
    """
    floor = config.grounding_floor if grounding_floor is None else grounding_floor
    ceiling = config.drop_ceiling if drop_ceiling is None else drop_ceiling

    # A decorative claim (no source_ids) is handled by contraction's decorative rule, not
    # here; the contamination test needs source_ids to remove.
    if not claim.source_ids:
        return False

    full = grounding(scalar, sources, claim.text)
    without = grounding_without(scalar, sources, claim.text, claim.source_ids)
    drop = full - without
    return without >= floor and drop < ceiling
