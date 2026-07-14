"""Slow integration test: the real NLI model on a handful of pairs.

Marked `slow` (deselected by default) because it downloads and runs the pinned ~400M DeBERTa
checkpoint. It sanity-checks direction (an entailed claim scores strictly above a contradicted
one) and measures throughput (pairs/sec), which it prints for the build report.

This is the only test that loads the model — every other test uses the injected stub scalar.
"""

from __future__ import annotations

import time

import pytest


@pytest.mark.slow
def test_direction_and_throughput(capsys):
    from closure_harness.nli import NLIScorer

    scorer = NLIScorer()

    entailed_sources = ["The store closes at 9pm on weekdays."]
    entailed_claim = "The store is open until 9pm on a Wednesday."
    contradicted_claim = "The store is closed all day on weekdays."

    s_entail = scorer(entailed_sources, entailed_claim)
    s_contra = scorer(entailed_sources, contradicted_claim)

    assert 0.0 <= s_contra < s_entail <= 1.0, (
        f"expected entailed > contradicted, got entail={s_entail:.3f} contra={s_contra:.3f}"
    )

    # Throughput: score a batch of distinct pairs and report pairs/sec. Each scalar() call
    # runs 2 directional pairs per source, so count directional pairs.
    claims = [f"Fact number {i} is asserted." for i in range(20)]
    n_pairs = 0
    start = time.perf_counter()
    for c in claims:
        scorer(entailed_sources, c)
        n_pairs += 2  # one source, bidirectional
    elapsed = time.perf_counter() - start
    pps = n_pairs / elapsed

    with capsys.disabled():
        print(
            f"\n[NLI throughput] device={scorer.device} "
            f"{n_pairs} directional pairs in {elapsed:.2f}s -> {pps:.1f} pairs/sec"
        )
    assert pps > 0


@pytest.mark.slow
def test_truncation_fails_closed():
    # Fail-closed on over-length input: a source longer than max_length must raise, not
    # silently clip (which would change what "grounded" means with no trace). Needs the real
    # tokenizer, so it lives here. A small max_length forces the boundary without huge text.
    import dataclasses

    from closure_harness.config import NLIConfig
    from closure_harness.nli import NLIScorer

    scorer = NLIScorer(dataclasses.replace(NLIConfig(), max_length=16))

    # Exactly at the cap must NOT raise; over the cap must raise.
    at_cap = " ".join(["word"] * 12)  # 16 tokens with the tiny source premise below
    assert 0.0 <= scorer(["ok"], at_cap) <= 1.0
    over_cap = " ".join(["word"] * 30)
    with pytest.raises(ValueError, match="exceeds max_length"):
        scorer(["ok"], over_cap)
