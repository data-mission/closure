"""E3 synthetic-validation instrument.

The modules here ARE the E3 analysis pipeline that a later, gated session will point at real
hidden states — not a mock of it. They are exercised first on planted fixtures whose right answer
is known by construction (``tests/``), the same anti-fishing ordering the harness uses
(``harness/tests/README.md``, E0 PLAN step 4): the analysis logic and the pre-registered
verdict-branch logic are validated while the data is still throwaway, so the instrument cannot be
tuned to a real result after the fact.

Pipeline stages, one module each:

- ``volume``  — the ground-truth semantic-volume statistic (e3-0002).
- ``probe``   — the ridge regression probe and the SEP-style logistic median-split baseline (e3-0001, e3-0003).
- ``splits``  — in-distribution and leave-one-family-out evaluation regimes (e3-0001).
- ``compare`` — AUROC and paired-bootstrap comparison of probe vs baseline (e3-0003).
- ``verdict`` — the pre-registered verdict-branch logic (E3 README § Verdict conditions),
  parameterized by thresholds that the registration fixes; this module invents none of them.
"""

from __future__ import annotations

__all__ = ["volume", "probe", "splits", "compare", "verdict"]
