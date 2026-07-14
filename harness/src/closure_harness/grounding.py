"""Leave-one-out grounding contrast (decision 0002).

grounding_drop(claim, s) = scalar(full sources) - scalar(sources minus s).

The E5 detector reads grounding as the NLI-only scalar (the deterministic reading noted in
the execution plan §8); no K-regeneration enters here. The scalar is injected so this module
carries no model dependency.
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
    """Scalar with the sources at drop_ids removed (positional index into sources)."""
    drop = set(drop_ids)
    kept = [s for i, s in enumerate(sources) if i not in drop]
    return scalar(kept, claim)


def grounding_drop(
    scalar: Scalar, sources: Sequence[str], claim: str, source_index: int
) -> float:
    """0002 contrast for a single source: scalar(full) - scalar(minus that source)."""
    return grounding(scalar, sources, claim) - grounding_without(
        scalar, sources, claim, [source_index]
    )
