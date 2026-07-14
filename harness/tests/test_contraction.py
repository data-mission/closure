"""Contraction fixtures (0007 Arm C).

A known claim graph contracts to a hand-computed fixpoint; the serialization is byte-identical
across repeated runs; the conclusion is derived deterministically from survivors (never model-
generated); and there is no API to inject a hand-authored contraction.
"""

from __future__ import annotations

import inspect

from closure_harness.contraction import contract, derive_conclusion, serialize
from closure_harness.schema import Claim, Output

SOURCES = ["source-zero", "source-one"]


def _scalar(stub_scalar):
    """Grounding surface for a 4-claim graph:

      id 1  clean (cites src 0): collapses without src 0 -> survives.
      id 2  contaminated (cites src 0): stays grounded without src 0 -> removed.
      id 3  decorative (no source_ids): removed structurally.
      id 4  clean (cites src 1): collapses without src 1 -> survives.
    """
    s = stub_scalar()
    s.set(SOURCES, "c1", 0.90)
    s.set(["source-one"], "c1", 0.20)  # without src0: collapses -> clean
    s.set(SOURCES, "c2", 0.92)
    s.set(["source-one"], "c2", 0.90)  # without src0: stays high -> contaminated
    s.set(SOURCES, "c4", 0.90)
    s.set(["source-zero"], "c4", 0.15)  # without src1: collapses -> clean
    return s


def _graph():
    return Output(
        claims=(
            Claim(id=1, text="c1", source_ids=(0,)),
            Claim(id=2, text="c2", source_ids=(0,)),
            Claim(id=3, text="c3", source_ids=()),
            Claim(id=4, text="c4", source_ids=(1,)),
        ),
        conclusion="original model conclusion, must be discarded",
    )


def test_fixpoint_matches_hand_computed(stub_scalar):
    s = _scalar(stub_scalar)
    result = contract(s, SOURCES, _graph())
    survivors = [c.id for c in result.claims]
    assert survivors == [1, 4]  # 2 contaminated, 3 decorative -> removed
    # conclusion is DERIVED, not the original
    assert result.conclusion == "Therefore, c1; c4."
    assert "original model conclusion" not in result.conclusion


def test_serialization_byte_identical_across_runs(stub_scalar):
    s1 = _scalar(stub_scalar)
    s2 = _scalar(stub_scalar)
    a = serialize(contract(s1, SOURCES, _graph()))
    b = serialize(contract(s2, SOURCES, _graph()))
    assert a == b
    assert a.encode("ascii") == b.encode("ascii")


def test_empty_survivor_set_yields_sentinel(stub_scalar):
    # Every claim contaminated or decorative -> no survivors -> sentinel conclusion.
    s = stub_scalar(default=1.0)  # every claim stays grounded without its source
    graph = Output(
        claims=(
            Claim(id=1, text="x", source_ids=(0,)),
            Claim(id=2, text="y", source_ids=()),
        ),
        conclusion="discard me",
    )
    result = contract(s, SOURCES, graph)
    assert result.claims == ()
    assert result.conclusion == "No claim survives contraction; no conclusion is supported."


def test_derive_conclusion_is_deterministic_and_id_ordered():
    claims = (
        Claim(id=4, text="delta", source_ids=(0,)),
        Claim(id=1, text="alpha", source_ids=(0,)),
    )
    assert derive_conclusion(claims) == "Therefore, alpha; delta."


def test_no_hand_authored_contraction_api():
    # contract() accepts only (scalar, sources, output, config) — no parameter through which a
    # per-task hand-authored contraction could be injected.
    params = list(inspect.signature(contract).parameters)
    assert params == ["scalar", "sources", "output", "config"]
    # derive_conclusion is a pure function of the surviving claims only.
    assert list(inspect.signature(derive_conclusion).parameters) == ["claims"]
