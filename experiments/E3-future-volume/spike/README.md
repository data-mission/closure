# E3 feasibility spike

Instrument check for E3: can the local host (Apple M4, 16 GB) load a 7B instruct model 4-bit,
extract the last-token pre-sampling hidden state (post-final-norm, pre-lm_head — the vector a
linear probe reads), and generate continuations at usable throughput. Verdict and measured
numbers: `../FEASIBILITY.md`.

Run:

```
uv run python run_spike.py
```

Downloads `mlx-community/Qwen2.5-7B-Instruct-4bit` (~4.3 GB) to the HuggingFace cache on first
run. Outputs land in `results/`: `spike_results.json` (every measured number) and
`hidden_states.npz` (the 20 extracted vectors, float32, shape 20×3584).

The 20 prompts hardcoded in `run_spike.py` are THROWAWAY — instrument-exercising data only,
never to appear in or seed the real E3 corpus.
