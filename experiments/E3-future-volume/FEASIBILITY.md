# E3 feasibility spike — hidden-state extraction and throughput on the local host

**mini hosts E3: yes — model Qwen2.5-7B-Instruct 4-bit (MLX), 24.2 tok/s generation, 129.0 tok/s prompt processing.**

Instrument check only, per the ordering in `LOG-e3.md`: prove the extraction point and the throughput on
disposable data before any design record is frozen or any real datum exists. Code and raw numbers:
`spike/run_spike.py`, `spike/results/spike_results.json`, `spike/results/hidden_states.npz`.

## Setup

- Hardware: Apple M4, 16 GB unified memory, macOS (Darwin 24.6.0).
- Model: `mlx-community/Qwen2.5-7B-Instruct-4bit` (group_size 64, 4-bit; `tie_word_embeddings: false`,
  28 layers, hidden_size 3584). Primary choice loaded and ran first try — the Llama-3.1-8B and
  transformers-on-MPS fallbacks were never needed.
- Stack: `uv` project at `spike/` — Python 3.12.13, mlx-lm 0.31.3, mlx 0.32.0, numpy, psutil.
- Seed 20260714 (`mx.random.seed`, re-seeded per generation run).

## Extraction point (verified against installed source, not memory)

The vector a linear probe reads is the final-layer hidden state at the last prompt token, after the final
RMSNorm, immediately before the lm_head projection. In mlx-lm 0.31.3, `mlx_lm/models/qwen2.py`:

- `Qwen2Model.__call__` (lines 137–155) runs the embedding, all 28 `TransformerBlock`s, and returns
  `self.norm(h)` — the post-final-norm hidden states, shape `(B, L, 3584)`.
- `Model.__call__` (lines 167–178) takes that output and applies the head:
  `self.lm_head(out)` when `tie_word_embeddings` is false (this checkpoint), else
  `self.model.embed_tokens.as_linear(out)`.

So `model.model(ids)[:, -1, :]` **is** the pre-sampling state, and no logits/hidden ambiguity exists in this
API — the inner module never sees the head.

**Sanity check: 20/20.** For every prompt, projecting the extracted vector through the head
(`lm_head`, mirroring `Model.__call__`) reproduces the exact top-1 next-token id of the normal full forward
pass. Max abs logit difference between the two paths: 0.03125 (fp16 accumulation noise; argmax identical in
all 20 cases). This rules out extracting a pre-norm, wrong-position, or wrong-layer tensor.

## Measured numbers

| quantity | value |
|---|---|
| model load time | 1.6 s (warm cache; 2.3 s first load) |
| hidden dim / dtype | 3584 / float16 |
| extraction latency per prompt (full forward, 33–52-token prompts) | mean 250 ms, min 244 ms, max 348 ms (first-call warmup) |
| sanity check (lm_head top-1 agreement) | 20/20 |
| prompt processing | mean 129.0 tok/s (range 109.2–161.8) |
| generation (128 tokens/run, temp 0.7, top-p 0.95, 5 runs) | mean 24.2 tok/s (range 24.16–24.27) |
| MLX peak memory | 4.44 GB |
| headroom vs 16 GB | 12.74 GB |
| RAM consumed by load (psutil available-RAM delta) | 3.50 GB |

Generation throughput was measured with `generate_step` consuming exactly 128 tokens per run without
stopping at EOS — a sustained-rate measurement, because the real ground-truth sampling generates
128–256-token continuations and short factual answers hitting EOS at ~10 tokens under-sample the
steady state. The per-run spread is 0.1 tok/s; the number is stable.

psutil available-RAM was 7.39 GB before load (other processes resident), 3.89 GB after load, 3.25 GB after
generation — the machine ran the whole spike without pressure. The 12.74 GB headroom figure is MLX peak vs
nominal 16 GB; the practical constraint is concurrent processes, not the model.

## Cost projection for E3 ground-truth sampling

At 24.2 tok/s generation and ~0.3 s prompt processing per pass, N = 10 continuations per prompt:

- 200 prompts × 10 × 128 tokens = 256k generated tokens → **~3.1 wall-clock hours** (2.9 h generation +
  prompt-pass overhead).
- 1000 prompts × 10 × 256 tokens = 2.56M generated tokens → **~30 wall-clock hours**.

Both are overnight-to-weekend jobs on this machine, unattended. Probe-input extraction is negligible by
comparison: 1000 prompts × 250 ms ≈ 4 minutes. A prompt cache shared across the N continuations of one
prompt would shave the (already small) prompt overhead; not needed for feasibility.

## Contamination rule

The 20 spike prompts hardcoded in `spike/run_spike.py` are **throwaway instruments**. They must never
appear in, or seed, the real E3 corpus — the instrument is proven on disposable data first, the same
anti-contamination ordering as E0 PLAN step 4 and the harness synthetic-fixtures convention. Any overlap
between the spike prompts and a future corpus item is a defect in the corpus.

## Fallbacks

None used. `mlx-community/Qwen2.5-7B-Instruct-4bit` downloaded (~4.3 GB), loaded, and passed every step on
the first attempt. Recorded for completeness: the planned fallback ladder was
`mlx-community/Meta-Llama-3.1-8B-Instruct-4bit`, then torch + transformers on MPS with
`output_hidden_states=True`.
