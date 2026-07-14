"""Leave-one-out grounding contrast (decision 0002).

grounding_drop(claim, s) = scalar(full sources) - scalar(sources minus s).

Inside the E5 contraction, grounding is the deterministic single-evaluation NLI scalar —
no K-regeneration averaging enters here, because regenerating model output inside Arm C
would void 0007's bit-for-bit reproducibility check (decision 0007, contamination detector).
0002's mean-over-K applies to the E0 measurement context, where scores aggregate over
model-regenerated outputs. The scalar is injected so this module carries no model dependency.
"""

from __future__ import annotations

from typing import Sequence

from .nli import Scalar


def grounding(scalar: Scalar, sources: Sequence[str], claim: str) -> float:
    """Scalar of a claim against the full retained source set."""
    return scalar(list(sources), claim)


def grounding_without(
    scalar: Scalar, sources: Sequence[str], claim: str, drop_ids: Sequence[int]
) -> float:
    """Scalar with the sources at drop_ids removed (positional index into sources).

    Out-of-range indices raise: a hallucinated citation index would otherwise remove
    nothing, force drop == 0, and mislabel the claim contaminated regardless of its real
    grounding. Such outputs belong in the pre-registered exclusion bucket, not the data.
    """
    drop = set(drop_ids)
    bad = [i for i in drop if i < 0 or i >= len(sources)]
    if bad:
        raise ValueError(
            f"source_ids {sorted(bad)} out of range for {len(sources)} sources"
        )
    kept = [s for i, s in enumerate(sources) if i not in drop]
    return scalar(kept, claim)


def grounding_drop(
    scalar: Scalar, sources: Sequence[str], claim: str, source_index: int
) -> float:
    """0002 contrast for a single source: scalar(full) - scalar(minus that source)."""
    return grounding(scalar, sources, claim) - grounding_without(
        scalar, sources, claim, [source_index]
    )
