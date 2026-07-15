# E3 pilot

Disposable-prompt pilot: the full E3 instrument exercised end to end on 30 THROWAWAY prompts on
the local host (Apple M4, 16 GB). Plumbing/tracer-bullet only — proves the whole pipeline runs and
produces finite numbers with sane dynamic range before any real corpus exists.

The 30 prompts in `run_pilot.py` are disposable. They MUST NEVER enter, seed, or otherwise touch
the real E3 corpus, and are distinct from the spike's 20 prompts.

- `run_pilot.py` — RESUMABLE runner. Writes `results/prompt_XX.json` (+ `results/prompt_XX.npz`
  for the hidden state and continuation embeddings) incrementally and skips prompts already done.
- `analyze_pilot.py` — reads `results/`, emits `results/summary.json` and prints distributions.

See `../PILOT.md` for the write-up (numbers, decision gaps, disclosure block).
