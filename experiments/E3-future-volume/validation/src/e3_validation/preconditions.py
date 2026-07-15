"""Precondition layer — the verdict cannot fire on empty evidence (audit-driven redesign, A).

The labeled dress rehearsal (REHEARSAL.md) fired the strongest verdict branch from a correctness arm
that carried ONE negative in 41 items: every correctness AUROC, the paired-bootstrap CI, and the
verbalized-margin branch were arithmetic on a single (and, as it happened, mislabeled) prompt. The
branch logic had no guard on the evidential mass of the correctness labels. This module is that
guard, plus the count-and-report discipline for excluded items the protocol already mandates
(README § Exclusion criteria; e3-0002; REGISTRATION § 3 validity precondition).

Two responsibilities:

  1. ``correctness_arm_evaluable`` — the pre-registered minimum-negatives gate. Below it the verdict
     is the terminal, HONEST state ``NOT_EVALUABLE_CORRECTNESS_ARM`` (verdict.py), never a refutation:
     the correctness comparison simply could not be run, which is a fact about the corpus, not
     evidence against H-VOL. ``min_negatives`` is a pre-registered parameter (VerdictThresholds); this
     module invents no value.

  2. ``exclusion_report`` — per-family counts of items excluded from the answerable subset (sampling
     failed to produce N valid continuations, or the item was unanswerable / gold-null), reported so
     the answerable subset the AUROCs run over is auditable and never silently selected.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence


def correctness_arm_evaluable(n_negatives: int, min_negatives: int) -> bool:
    """True iff the answerable subset carries at least ``min_negatives`` negatives.

    A negative is an answerable item labeled incorrect — the class an AUROC needs on the low side.
    With fewer than ``min_negatives`` of them the correctness AUROCs and their paired bootstrap are
    determined by a handful of labels (rehearsal: one), so the correctness arm is not evaluable and
    the verdict is terminal-honest rather than confirmed or refuted.
    """
    if min_negatives < 0:
        raise ValueError(f"min_negatives must be non-negative; got {min_negatives}")
    return n_negatives >= min_negatives


@dataclass(frozen=True)
class ExclusionReport:
    """Per-family exclusion accounting for the answerable subset.

    Fields:
        per_family_excluded: family label -> count of items excluded from the answerable subset.
        per_family_answerable: family label -> count of items retained in the answerable subset.
        total_excluded, total_answerable: totals across families.
    """

    per_family_excluded: Mapping[str, int]
    per_family_answerable: Mapping[str, int]
    total_excluded: int
    total_answerable: int


def exclusion_report(
    family_labels: Sequence[str], excluded_mask: Sequence[bool]
) -> ExclusionReport:
    """Tally exclusions per family from a boolean mask aligned to ``family_labels``.

    Args:
        family_labels: per-item family label.
        excluded_mask: per-item flag, True iff the item is excluded from the answerable subset
            (sampling failed to yield N valid continuations, or the item has no gold). Never set on
            probe error — OOD and hard cases are the test, not noise (README § Exclusion criteria).

    Returns:
        An ``ExclusionReport`` with per-family and total counts. Deterministic; sorted by label in
        the dict construction so the report serializes stably.
    """
    fams = list(family_labels)
    mask = list(excluded_mask)
    if len(fams) != len(mask):
        raise ValueError("family_labels and excluded_mask must be the same length")

    excluded: Counter[str] = Counter()
    answerable: Counter[str] = Counter()
    for fam, is_excluded in zip(fams, mask):
        if is_excluded:
            excluded[fam] += 1
        else:
            answerable[fam] += 1

    all_families = sorted(set(fams))
    per_excluded = {f: int(excluded.get(f, 0)) for f in all_families}
    per_answerable = {f: int(answerable.get(f, 0)) for f in all_families}
    return ExclusionReport(
        per_family_excluded=per_excluded,
        per_family_answerable=per_answerable,
        total_excluded=int(sum(per_excluded.values())),
        total_answerable=int(sum(per_answerable.values())),
    )
