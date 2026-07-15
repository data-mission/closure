# E3 confirmatory run

The full frozen E3 instrument on the 200-prompt confirmatory corpus (`../corpus/candidates.jsonl`),
executed by `run_experiment.py`. Reuses the proven per-prompt pipeline from `../pilot/run_pilot.py`
and `../rehearsal/run_rehearsal.py` verbatim in structure, adds the frozen correctness/normalizer/
B1-variant/refusal contract, and calls the `e3_validation` package (volume, freeze, loader) rather
than reimplementing it.

Per prompt: (1) chat-template + single forward pass -> post-final-norm hidden state (fp32) + B3
next-token entropy; (2) 10 seeded continuations (temp 0.7 / top-p 0.95, cap 256, early EOS kept),
refusal-counted; (3) nomic-embed (clustering: prefix, dim 768, CPU) -> semantic volume; (4)
answerable only: greedy answer (cap 768) scored by the improved normalizer against gold; (5) B1
verbalized confidence, both the frozen zero-shot elicitation and the chain-of-thought variant.

RESUMABLE: writes `results/prompt_XXX.json` (+ `.npz`) per prompt, skips any already present.

Manifest: `results/run_manifest.json` — the frozen config (via `e3_validation.freeze`) with its
committed SHA-256, plus registration status and start timestamp. Written before the first prompt.

Run: `uv run python run_experiment.py` (HF cache offline; no remote APIs).
