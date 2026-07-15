"""
E3 feasibility spike — last-token pre-sampling hidden-state extraction + throughput.

Instrument check only. Answers one question with measured numbers: can this machine
(Apple M4, 16 GB) host E3 — load a ~7-8B instruct model 4-bit locally, extract the
LAST-TOKEN PRE-SAMPLING HIDDEN STATE (final-layer hidden state at the last prompt token,
after the final norm, immediately before the lm_head projection — the vector a linear
probe reads), and generate continuations at usable throughput.

Extraction point verified against installed source
(.venv/.../mlx_lm/models/qwen2.py, mlx-lm 0.31.3):
  - Qwen2Model.__call__ (lines 137-155) runs all TransformerBlocks then returns
    `self.norm(h)` — the post-final-RMSNorm hidden state. This is the pre-lm_head vector.
  - Model.__call__ (lines 167-178) takes that and applies the head:
      tie_word_embeddings -> self.model.embed_tokens.as_linear(out)
      else                -> self.lm_head(out)
  So `model.model(ids)[:, -1, :]` IS the pre-sampling state; applying the head to it
  reproduces the top-1 next token from the normal forward pass `model(ids)[:, -1, :]`.
  The sanity check (step d) proves this empirically for all 20 prompts.

THROWAWAY DATA: the 20 prompts below are disposable instrument-exercising prompts.
They must NEVER appear in, or seed, the real E3 corpus. Anti-contamination ordering:
the instrument is proven on disposable data first (same convention as E0 PLAN step 4
and the harness synthetic-fixtures rule).
"""

import gc
import json
import sys
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
import psutil
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.sample_utils import make_sampler

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
MODEL_ID = "mlx-community/Qwen2.5-7B-Instruct-4bit"
SEED = 20260714
GEN_TOKENS = 128
GEN_TEMP = 0.7
GEN_TOP_P = 0.95
N_GEN_PROMPTS = 5
TOTAL_RAM_BYTES = 16 * 1024**3  # nominal 16 GB unified memory

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 20 THROWAWAY prompts — disposable instrument fodder, NEVER for the real corpus.
# Spread low->high expected continuation diversity: factual (near-deterministic),
# math (single answer), instruction-following, ambiguous, open-ended creative.
# ---------------------------------------------------------------------------
THROWAWAY_PROMPTS = [
    # factual / low diversity
    "What is the capital of France?",
    "How many continents are there on Earth?",
    "What year did the Apollo 11 mission land on the Moon?",
    "What is the chemical symbol for gold?",
    "Who wrote the play 'Romeo and Juliet'?",
    # math / single answer
    "What is 17 multiplied by 23?",
    "If a train travels 60 km in 45 minutes, what is its average speed in km/h?",
    "What is the derivative of x^3 with respect to x?",
    "Compute the sum of the first 10 positive integers.",
    # instruction-following / constrained
    "List three primary colors, separated by commas.",
    "Rewrite this sentence in the past tense: 'She walks to the store.'",
    "Translate the word 'hello' into Spanish.",
    "Give a one-word antonym for 'hot'.",
    # ambiguous / underspecified (higher diversity)
    "Is it going to rain tomorrow?",
    "What should I have for dinner?",
    "Which is better?",
    "What does this mean?",
    # open-ended creative / high diversity
    "Write the opening line of a mystery novel.",
    "Describe an imaginary color that does not exist.",
    "Invent a name for a new planet and say one thing about it.",
]
assert len(THROWAWAY_PROMPTS) == 20


def avail_ram_bytes():
    return psutil.virtual_memory().available


def head_logits(model, h):
    """Apply the model's output head to a post-final-norm hidden state `h`.

    Mirrors Model.__call__ (mlx_lm/models/qwen2.py:167-178) exactly, so the logits
    returned here are identical to those the normal forward pass produces.
    """
    if getattr(model.args, "tie_word_embeddings", False):
        return model.model.embed_tokens.as_linear(h)
    return model.lm_head(h)


def main():
    results = {
        "model_id": MODEL_ID,
        "mlx_version": mx.__version__,
        "python_version": sys.version.split()[0],
        "seed": SEED,
        "total_ram_bytes_nominal": TOTAL_RAM_BYTES,
    }
    try:
        import mlx_lm

        results["mlx_lm_version"] = mlx_lm.__version__
    except Exception:
        results["mlx_lm_version"] = "unknown"

    mx.random.seed(SEED)

    # --- (a) load: time + memory ------------------------------------------
    ram_before_load = avail_ram_bytes()
    t0 = time.perf_counter()
    model, tokenizer = load(MODEL_ID)
    load_time_s = time.perf_counter() - t0
    ram_after_load = avail_ram_bytes()

    # force weights resident so peak/active memory reflects the loaded model
    mx.eval(model.parameters())
    peak_after_load_bytes = mx.get_peak_memory()

    results["load_time_s"] = load_time_s
    results["ram_available_before_load_bytes"] = ram_before_load
    results["ram_available_after_load_bytes"] = ram_after_load
    results["ram_consumed_by_load_bytes"] = ram_before_load - ram_after_load
    results["mlx_peak_memory_after_load_bytes"] = peak_after_load_bytes
    results["tie_word_embeddings"] = bool(
        getattr(model.args, "tie_word_embeddings", False)
    )

    print(f"[load] {load_time_s:.2f}s  "
          f"mlx_peak={peak_after_load_bytes/1e9:.2f}GB  "
          f"ram_consumed={(ram_before_load-ram_after_load)/1e9:.2f}GB")

    # --- (c) + (d) extraction and sanity check per prompt -----------------
    per_prompt = []
    vectors = []
    hidden_dim = None
    hidden_dtype = None
    sanity_pass = 0

    for i, prompt in enumerate(THROWAWAY_PROMPTS):
        messages = [{"role": "user", "content": prompt}]
        ids = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True
        )
        x = mx.array([ids])  # (1, L)
        prompt_len = len(ids)

        te = time.perf_counter()
        # post-final-norm hidden states for every position: (1, L, hidden)
        h_all = model.model(x)
        h_last = h_all[:, -1, :]  # (1, hidden) — the pre-sampling state
        mx.eval(h_last)
        extract_time_s = time.perf_counter() - te

        # full normal forward pass -> logits at last position
        logits_full = model(x)[:, -1, :]  # (1, vocab)
        top1_full = int(mx.argmax(logits_full, axis=-1).item())

        # project extracted hidden state through the head
        logits_from_h = head_logits(model, h_last)  # (1, vocab)
        top1_from_h = int(mx.argmax(logits_from_h, axis=-1).item())

        # numerical agreement of the two logit tensors (should be ~exact)
        max_abs_logit_diff = float(mx.max(mx.abs(logits_full - logits_from_h)).item())

        ok = top1_full == top1_from_h
        sanity_pass += int(ok)

        vec = np.array(h_last[0], dtype=np.float32)
        vectors.append(vec)
        if hidden_dim is None:
            hidden_dim = int(h_last.shape[-1])
            hidden_dtype = str(h_last.dtype)

        top1_tok = tokenizer.decode([top1_full])
        per_prompt.append({
            "idx": i,
            "prompt": prompt,
            "prompt_tokens": prompt_len,
            "extract_time_s": extract_time_s,
            "top1_token_id": top1_full,
            "top1_token_str": top1_tok,
            "sanity_top1_match": ok,
            "max_abs_logit_diff": max_abs_logit_diff,
        })
        print(f"[extract {i:2d}] len={prompt_len:3d} "
              f"t={extract_time_s*1000:6.1f}ms top1={top1_tok!r} "
              f"match={ok} dlogit={max_abs_logit_diff:.2e}")

    hidden = np.stack(vectors, axis=0)  # (20, hidden_dim)
    npz_path = RESULTS_DIR / "hidden_states.npz"
    np.savez(
        npz_path,
        hidden_states=hidden,
        prompt_index=np.arange(len(THROWAWAY_PROMPTS)),
    )

    extract_times = [p["extract_time_s"] for p in per_prompt]
    results["hidden_dim"] = hidden_dim
    results["hidden_dtype"] = hidden_dtype
    results["hidden_states_npz"] = str(npz_path)
    results["hidden_states_shape"] = list(hidden.shape)
    results["extract_time_s_mean"] = float(np.mean(extract_times))
    results["extract_time_s_min"] = float(np.min(extract_times))
    results["extract_time_s_max"] = float(np.max(extract_times))
    results["sanity_top1_match_count"] = sanity_pass
    results["sanity_top1_match_total"] = len(THROWAWAY_PROMPTS)
    results["sanity_max_abs_logit_diff"] = max(
        p["max_abs_logit_diff"] for p in per_prompt
    )
    results["per_prompt"] = per_prompt

    print(f"[sanity] top1 match {sanity_pass}/{len(THROWAWAY_PROMPTS)}  "
          f"hidden_dim={hidden_dim} dtype={hidden_dtype}")

    # --- (e) generation throughput ----------------------------------------
    # Uses generate_step directly and consumes exactly GEN_TOKENS tokens per run,
    # NOT stopping at EOS: this is a sustained-throughput measurement (the real E3
    # ground-truth sampling generates 128-256-token continuations; short factual
    # answers hitting EOS at ~10 tokens would under-sample the steady-state rate).
    # Sampling is temp>0, top-p, seeded per run. Prompt spread: one factual, one
    # math, one instruction, one ambiguous, one creative.
    sampler = make_sampler(temp=GEN_TEMP, top_p=GEN_TOP_P)
    gen_prompt_indices = [0, 6, 10, 14, 17]
    gen_runs = []
    for i in gen_prompt_indices:
        prompt = THROWAWAY_PROMPTS[i]
        messages = [{"role": "user", "content": prompt}]
        ids = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True
        )
        prompt_arr = mx.array(ids)
        mx.random.seed(SEED + i)  # seeded, reproducible
        tokens = []
        tic = time.perf_counter()
        t_first = None
        for token, _logprobs in generate_step(
            prompt_arr, model, max_tokens=GEN_TOKENS, sampler=sampler
        ):
            if t_first is None:
                t_first = time.perf_counter()
            tokens.append(int(token))
        t_end = time.perf_counter()
        prompt_time = t_first - tic  # time to first token = prompt processing
        gen_time = t_end - t_first  # remaining tokens
        prompt_tps = len(ids) / prompt_time
        gen_tps = (len(tokens) - 1) / gen_time if gen_time > 0 else float("nan")
        gen_runs.append({
            "prompt_idx": i,
            "prompt": prompt,
            "prompt_tokens": len(ids),
            "generation_tokens": len(tokens),
            "prompt_tps": prompt_tps,
            "generation_tps": gen_tps,
            "prompt_time_s": prompt_time,
            "generation_time_s": gen_time,
            "peak_memory_gb": mx.get_peak_memory() / 1e9,
            "eos_ignored": True,
        })
        print(f"[gen p{i}] prompt_tps={prompt_tps:.1f} "
              f"gen_tps={gen_tps:.1f} "
              f"gen_tokens={len(tokens)} "
              f"peak={mx.get_peak_memory()/1e9:.2f}GB")

    results["generation"] = {
        "gen_tokens_requested": GEN_TOKENS,
        "temp": GEN_TEMP,
        "top_p": GEN_TOP_P,
        "n_prompts": N_GEN_PROMPTS,
        "eos_ignored_note": (
            "generate_step consumed exactly gen_tokens_requested tokens per run "
            "without stopping at EOS — sustained-throughput measurement"
        ),
        "runs": gen_runs,
        "prompt_tps_mean": float(np.mean([g["prompt_tps"] for g in gen_runs])),
        "generation_tps_mean": float(np.mean([g["generation_tps"] for g in gen_runs])),
        "prompt_tps_min": float(np.min([g["prompt_tps"] for g in gen_runs])),
        "prompt_tps_max": float(np.max([g["prompt_tps"] for g in gen_runs])),
        "generation_tps_min": float(np.min([g["generation_tps"] for g in gen_runs])),
        "generation_tps_max": float(np.max([g["generation_tps"] for g in gen_runs])),
    }

    # --- (f) memory after generation --------------------------------------
    ram_after_gen = avail_ram_bytes()
    peak_bytes = mx.get_peak_memory()
    results["ram_available_after_gen_bytes"] = ram_after_gen
    results["mlx_peak_memory_bytes"] = peak_bytes
    results["mlx_peak_memory_gb"] = peak_bytes / 1e9
    results["headroom_vs_16gb_bytes"] = TOTAL_RAM_BYTES - peak_bytes
    results["headroom_vs_16gb_gb"] = (TOTAL_RAM_BYTES - peak_bytes) / 1e9
    results["min_ram_available_observed_bytes"] = min(
        ram_after_load, ram_after_gen
    )

    print(f"[memory] mlx_peak={peak_bytes/1e9:.2f}GB "
          f"headroom_vs_16GB={(TOTAL_RAM_BYTES-peak_bytes)/1e9:.2f}GB "
          f"ram_avail_after_gen={ram_after_gen/1e9:.2f}GB")

    # --- (g) write results.json -------------------------------------------
    out_path = RESULTS_DIR / "spike_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[done] wrote {out_path}")

    del model
    gc.collect()


if __name__ == "__main__":
    main()
