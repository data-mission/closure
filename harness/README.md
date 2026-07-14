# closure-harness

The measurement slice for experiment E5 (mechanical reclosure vs instructed disregard). It
implements only what E5 needs — the grounding (G) machinery, the contamination detector, Arm C's
deterministic contraction, ground-truth outcome scoring, and the comparison test. Rigidity (R),
preserved-ambiguity (P), and factor analysis are out of scope until E0/E4.

The methodology is frozen in the repo's decision records; this package is their executable form:

| module | decision | role |
|---|---|---|
| `config.py` | 0001/0002/0006/0007 | every tunable, frozen; sorted-key JSON -> SHA-256 freeze token |
| `nli.py` | 0002 | pinned DeBERTa-MNLI grounding scalar `(P(entail)-P(contradict)+1)/2`, bidirectional, max over sources |
| `grounding.py` | 0002 | leave-one-out contrast `scalar(full) - scalar(minus s)` |
| `detector.py` | 0007 | contamination rule; drives Arm C only, never the outcome |
| `contraction.py` | 0007 | Arm C: deterministic contraction to a fixpoint, conclusion DERIVED not regenerated |
| `outcomes.py` | 0007 | ground-truth scoring (contamination + completeness); imports `nli`, never `detector` |
| `stats.py` | 0007 | two-proportion z-test (Bonferroni x3), MDE for N=60, completeness non-inferiority (δ=0.10) |
| `generate.py` | 0001 | provider-agnostic generation; validates schema; halts on model-identity mismatch |

The NLI scalar is injected everywhere (a `Scalar` callable), so the logic is unit-tested against a
stub scalar with no model load. The single real-model check is `slow`-marked.

## Environment

```
uv sync                              # create .venv from the committed uv.lock
uv run pytest -m "not slow"          # fast synthetic suite
uv run pytest -m slow                # real NLI model: direction + throughput
uv run python scripts/check_config_freeze.py   # fails on config drift vs config.sha256
```

`.python-version`, `uv.lock`, and `config.sha256` are committed: the environment and the frozen
config are both reproducible and drift-checkable. The config hash is the token a reader matches
against the OSF pre-registration to confirm the analysis plan predated the data.
