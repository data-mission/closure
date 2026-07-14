"""Shared test fixtures.

The NLI scalar is injected everywhere, so unit tests use a programmable stub scalar and never
load the real model. This is deliberate: the fixtures below are committed BEFORE any real data
or model run exists — validating the detector/contraction/outcome/stats logic on synthetic,
hand-computed cases is the anti-fishing point (mirrors E0 PLAN.md step 4). The one real-model
check lives in test_nli_integration.py behind the `slow` marker.
"""

from __future__ import annotations

from typing import Callable, Sequence

import pytest


class StubScalar:
    """Programmable grounding scalar for tests.

    Backed by a table keyed on (tuple(sorted(sources)), claim) -> float. Unlisted keys return
    the default. This lets a fixture plant an exact grounding surface: e.g. a claim that stays
    high with its source removed (contaminated) vs one that collapses (clean).
    """

    def __init__(self, table: dict | None = None, default: float = 0.0):
        self.table = dict(table or {})
        self.default = default
        self.calls: list[tuple[tuple[str, ...], str]] = []

    def key(self, sources: Sequence[str], claim: str) -> tuple[tuple[str, ...], str]:
        return (tuple(sorted(sources)), claim)

    def set(self, sources: Sequence[str], claim: str, value: float) -> None:
        self.table[self.key(sources, claim)] = value

    def __call__(self, sources: Sequence[str], claim: str) -> float:
        k = self.key(sources, claim)
        self.calls.append(k)
        return self.table.get(k, self.default)


@pytest.fixture
def stub_scalar() -> Callable[..., StubScalar]:
    def _make(table: dict | None = None, default: float = 0.0) -> StubScalar:
        return StubScalar(table=table, default=default)

    return _make
