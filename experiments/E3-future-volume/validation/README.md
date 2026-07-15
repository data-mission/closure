# E3 synthetic validation

The E3 analysis pipeline and its pre-registered verdict-branch logic, proven on planted,
**throwaway** fixtures whose right answer is known by construction — before any real corpus,
generation, or model run exists. This mirrors the harness's synthetic-fixtures convention
(`harness/tests/README.md`, E0 PLAN step 4): the anti-fishing point is that the instrument cannot
be tuned to a real result after the fact, because it was validated while the data was still
disposable.

The modules under `src/e3_validation/` **are** the E3 analysis instrument a later, gated session
will point at real hidden states — not a mock of it.

- `volume.py`  — `log det(G + 1e-6 I)` over mean-centered, L2-normalized embeddings (e3-0002).
- `probe.py`   — ridge probe (train-only z-score + inner-CV alpha) and SEP-style logistic
  median-split baseline (e3-0001, e3-0003).
- `splits.py`  — in-distribution split and leave-one-family-out OOD rotation (e3-0001).
- `compare.py` — AUROC and paired-bootstrap CI for probe-vs-baseline (e3-0003).
- `verdict.py` — the pre-registered branch logic, parameterized by thresholds the registration
  fixes; this code invents no threshold value.

Fixture classes and their planted answers, plus the open verdict thresholds, are documented in
`../VALIDATION.md`.

```
uv sync
uv run pytest
```
