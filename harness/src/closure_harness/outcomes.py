"""Ground-truth outcome scoring (decision 0007, repaired).

Two annotation sets are authored at task-construction time, independent of any model output:
  must_change  — conclusions that must change under not-A (A-dependent).
  must_persist — conclusions that must survive under not-A (independent of A).

An arm output "still asserts" an annotated conclusion iff the bidirectional NLI scalar of
that conclusion against the arm's asserted text is >= the config assert_threshold.

  contamination = fraction of must_change conclusions the output still asserts   (lower is better)
  completeness  = fraction of must_persist conclusions the output still asserts   (higher is better)

Scoring is identical across all arms and referenced only to the annotations — never to the
detector that built Arm C. This module imports nli.py; it MUST NOT import detector.py
(0007 separation, enforced by tests/test_import_hygiene.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .config import CONFIG, OutcomeConfig
from .nli import Scalar
from .schema import Output


@dataclass(frozen=True)
class Annotations:
    must_change: tuple[str, ...]
    must_persist: tuple[str, ...]


@dataclass(frozen=True)
class Score:
    contamination: float
    completeness: float


def _asserted_text(output: Output) -> list[str]:
    """The premises an arm output asserts: its conclusion plus every surviving claim text.

    An annotated conclusion counts as still-asserted if ANY of these entails it (max over
    premises, matching the 0002 multi-source aggregation). An output that deleted everything
    asserts only the empty-support sentinel conclusion, so it fails to entail any must_change
    (contamination 0) AND any must_persist (completeness 0) — the deletion trap is caught by
    scoring both sides against the same asserted set.
    """
    return [output.conclusion, *(c.text for c in output.claims)]


def _still_asserts(scalar: Scalar, output: Output, conclusion: str, threshold: float) -> bool:
    premises = _asserted_text(output)
    return scalar(premises, conclusion) >= threshold


def score(
    scalar: Scalar,
    output: Output,
    annotations: Annotations,
    config: OutcomeConfig = CONFIG.outcome,
) -> Score:
    """Contamination and completeness for one arm output against the task annotations.

    An empty annotation set yields 0.0 for that dimension (no items to still-assert).
    """
    t = config.assert_threshold

    change = annotations.must_change
    persist = annotations.must_persist

    contamination = (
        sum(1 for c in change if _still_asserts(scalar, output, c, t)) / len(change)
        if change
        else 0.0
    )
    completeness = (
        sum(1 for c in persist if _still_asserts(scalar, output, c, t)) / len(persist)
        if persist
        else 0.0
    )
    return Score(contamination=contamination, completeness=completeness)


def contamination_rate(scores: Sequence[Score]) -> float:
    """Mean contamination across tasks (arm-level rate for the z-test)."""
    return sum(s.contamination for s in scores) / len(scores) if scores else 0.0


def completeness_rate(scores: Sequence[Score]) -> float:
    return sum(s.completeness for s in scores) / len(scores) if scores else 0.0
