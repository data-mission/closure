# Harness tests

Synthetic-only fixtures, committed before any real corpus, generation, or model run exists —
validating the detector, contraction, outcome, and stats logic on hand-computed cases while the
data is still throwaway is the anti-fishing point (mirrors E0 PLAN.md step 4).

- All unit tests inject a stub grounding scalar (`tests/conftest.py`); they never load the model.
- `test_nli_integration.py` is the single real-model check, marked `slow`. Run it with
  `uv run pytest -m slow`; the fast suite is `uv run pytest -m "not slow"`.
