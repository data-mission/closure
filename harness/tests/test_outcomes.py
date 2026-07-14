"""Outcome fixtures (0007 repaired scoring).

Synthetic arm outputs vs annotation sets with known contamination/completeness fractions ->
scorer returns the exact fractions. Includes the deletion trap: an output that deleted
everything scores contamination 0 AND completeness 0 (winning contamination by deletion is
caught, because completeness collapses too).
"""

from __future__ import annotations

import pytest

from closure_harness.config import CONFIG
from closure_harness.outcomes import Annotations, contamination_rate, completeness_rate, score
from closure_harness.schema import Claim, Output

T = CONFIG.outcome.assert_threshold  # 0.7


def _output():
    return Output(
        claims=(
            Claim(id=1, text="claim-a", source_ids=(0,)),
            Claim(id=2, text="claim-b", source_ids=(1,)),
        ),
        conclusion="the-conclusion",
    )


def _asserted_key(out: Output, target: str):
    # Mirror outcomes._asserted_text ordering, then the stub's sorted-source keying.
    premises = [out.conclusion, *(c.text for c in out.claims)]
    return (tuple(sorted(premises)), target)


def test_known_fractions(stub_scalar):
    out = _output()
    # must_change: 2 conclusions, 1 still asserted (>= T), 1 not -> contamination 1/2.
    # must_persist: 2 conclusions, 2 still asserted -> completeness 2/2.
    s = stub_scalar(default=0.0)
    s.table[_asserted_key(out, "mc-asserted")] = 0.85
    s.table[_asserted_key(out, "mc-dropped")] = 0.30
    s.table[_asserted_key(out, "mp-kept-1")] = 0.90
    s.table[_asserted_key(out, "mp-kept-2")] = 0.70  # exactly at threshold -> asserted (>=)
    ann = Annotations(
        must_change=("mc-asserted", "mc-dropped"),
        must_persist=("mp-kept-1", "mp-kept-2"),
    )
    result = score(s, out, ann)
    assert result.contamination == 0.5
    assert result.completeness == 1.0


def test_threshold_is_inclusive(stub_scalar):
    out = _output()
    s = stub_scalar(default=0.0)
    s.table[_asserted_key(out, "exact")] = T  # exactly threshold
    s.table[_asserted_key(out, "below")] = T - 1e-9
    s.table[_asserted_key(out, "kept")] = 1.0
    ann = Annotations(must_change=("exact", "below"), must_persist=("kept",))
    assert score(s, out, ann).contamination == 0.5


def test_deletion_trap(stub_scalar):
    # An arm that deleted everything: no claims, sentinel conclusion. It entails neither the
    # must_change nor the must_persist conclusions -> contamination 0 AND completeness 0.
    deleted = Output(claims=(), conclusion="No claim survives contraction; no conclusion is supported.")
    s = stub_scalar(default=0.0)  # sentinel entails nothing annotated
    ann = Annotations(
        must_change=("mc-1", "mc-2"),
        must_persist=("mp-1", "mp-2", "mp-3"),
    )
    result = score(s, deleted, ann)
    assert result.contamination == 0.0
    assert result.completeness == 0.0  # the trap: cleanliness bought by gutting is visible here


def test_empty_annotation_sets_raise(stub_scalar):
    # An empty set means a broken task slipped past corpus exclusion: fail loudly. Silent
    # 0.0 would score every arm worst-possible completeness (or best-possible
    # contamination) on that task, distorting rates without a trace.
    out = _output()
    s = stub_scalar(default=1.0)
    with pytest.raises(ValueError, match="non-empty"):
        score(s, out, Annotations(must_change=(), must_persist=()))
    with pytest.raises(ValueError, match="non-empty"):
        score(s, out, Annotations(must_change=("x",), must_persist=()))
    with pytest.raises(ValueError, match="non-empty"):
        score(s, out, Annotations(must_change=(), must_persist=("x",)))


def test_arm_level_rates(stub_scalar):
    out = _output()
    s = stub_scalar(default=0.0)
    s.table[_asserted_key(out, "x")] = 0.9
    ann_hi = Annotations(must_change=("x",), must_persist=("x",))
    ann_lo = Annotations(must_change=("y",), must_persist=("y",))
    scores = [score(s, out, ann_hi), score(s, out, ann_lo)]
    assert contamination_rate(scores) == 0.5
    assert completeness_rate(scores) == 0.5
