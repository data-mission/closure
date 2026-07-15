# E3 labeled dress rehearsal

The full E3 instrument AND the full downstream analysis path (ridge probe, SEP median-split,
correctness AUROCs, paired bootstrap, verdict branch) run end to end on 41 THROWAWAY LABELED
prompts, to (a) eyeball every number the real 200-prompt run would print for scale robustness and
(b) measure where Qwen2.5-7B's accuracy breaks by difficulty, calibrating the planned corpus
hardening. Report: `../REHEARSAL.md`. All numbers DESCRIPTIVE at n=41; nothing here is evidence
about H-VOL; the prompts must never enter the real corpus.

- `run_rehearsal.py` — the 41 prompts (family, difficulty 1-4, verified gold) + the per-prompt
  pipeline (pilot pattern; adds a dedicated greedy answer scored for correctness). Resumable.
- `normalizer.py` — concrete implementation of the CORPUS.md § Labeling protocol scoring rule;
  its docstring records where that spec was too vague to implement (findings V1-V5).
- `disjointness.py` — exact-overlap + max-Jaccard check vs spike-20 / pilot-30 / corpus-200.
- `analyze_rehearsal.py` — the entire stats path, CALLING `e3_validation` throughout; calibration
  outputs (accuracy-by-difficulty, CI widths at n=41 and extrapolated to n=126); confounds;
  volume split-half reliability.
- `results/` — per-prompt JSON + npz, `run_config.json`, `analysis.json`, `disjointness.json`,
  `run.log`.

Run: `uv sync`, then `uv run python run_rehearsal.py`, then `uv run python analyze_rehearsal.py`.
Base seed 20260714; derived analysis seeds documented in `analyze_rehearsal.py`.
