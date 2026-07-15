"""
E3 disposable-prompt pilot — the FULL E3 instrument, end to end, on 30 THROWAWAY prompts.

Tracer-bullet / plumbing run. Per prompt it executes the entire real pipeline exactly as the
decision records fix it:

  (1) e3-0001 extraction: chat-template the prompt, one forward pass with NO generation, take the
      post-final-RMSNorm hidden state at the last prompt token — `model.model(ids)[:, -1, :]` —
      the pre-sampling vector the lm_head reads (fp16 -> fp32). From the SAME forward pass, the
      next-token distribution (head applied to that exact hidden state) gives B3, the naive
      predictive entropy (e3-0003 B3).
  (2) e3-0002 ground truth: N = 10 seeded continuations, temperature 0.7 / top-p 0.95, max 256
      tokens with early EOS kept. Seed per draw = base_seed + prompt_index * N + draw_index
      (base_seed = 20260714). Realized lengths and wall time recorded.
  (3) embed the 10 continuations with nomic-ai/nomic-embed-text-v1.5 (pinned revision, output dim
      768, CPU) and compute the volume by CALLING the validation package's `semantic_volume`
      (e3-0002 formula: log det(G + 1e-6 I) over mean-centered-then-L2-normalized embeddings).
  (4) e3-0003 B1: two-turn verbalized confidence with the frozen verbatim elicitation, greedy
      decode, first-integer-0-100 parse, one identical retry, missing counted.

NOMIC PREFIX DECISION GAP: nomic-embed v1.5 REQUIRES a task prefix
(search_document / search_query / classification / clustering). e3-0002 does NOT fix this choice.
This pilot uses "clustering: " (diversity/dispersion measurement is the clustering-family use).
THIS IS A DECISION GAP the records must close before freeze — flagged in PILOT.md and the report.

RESUMABLE: writes results/prompt_XX.json (+ prompt_XX.npz for the hidden state and the 10
continuation embeddings) incrementally and skips any prompt whose JSON already exists, so it can
be run in bounded chunks.

THROWAWAY DATA: the 30 prompts below are disposable instrument fodder. They MUST NEVER appear in,
or seed, the real E3 corpus, and are distinct from the spike's 20 prompts.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.sample_utils import make_sampler

from e3_validation.volume import semantic_volume

# ---------------------------------------------------------------------------
# config (all pins per e3-0002 / e3-0003 / e3-0004)
# ---------------------------------------------------------------------------
MODEL_ID = "mlx-community/Qwen2.5-7B-Instruct-4bit"
MODEL_REVISION = "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed"  # e3-0004 pin (provenance)

BASE_SEED = 20260714
N_GEN = 10
GEN_TEMP = 0.7
GEN_TOP_P = 0.95
MAX_TOKENS = 256

# Embedding model (e3-0002 / e3-0004). Revision pinned to the snapshot downloaded for this pilot.
NOMIC_MODEL = "nomic-ai/nomic-embed-text-v1.5"
NOMIC_REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"
NOMIC_DIM = 768  # full Matryoshka width, frozen per e3-0002 (NOT a library default)
# DECISION GAP (see module docstring): nomic v1.5 requires a task prefix; e3-0002 does not fix it.
NOMIC_PREFIX = "clustering: "

# B1 verbalized-confidence elicitation — FROZEN VERBATIM per e3-0003.
VC_ELICITATION = (
    "On a scale from 0 to 100, what is the probability that your answer above is correct? "
    "Reply with a single integer between 0 and 100 and nothing else."
)

ENTROPY_BASE = "nats"  # Shannon entropy computed with natural log; base recorded (e3-0003 fixes
# neither base — descriptive plumbing statistic).

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 30 THROWAWAY prompts — disposable, distinct from the spike's 20, 6 per kind.
# Spread low -> high expected continuation diversity so the volume statistic's
# dynamic range across kinds is visible.
# ---------------------------------------------------------------------------
PROMPTS = [
    # ---- factual QA (low diversity) ----
    ("factual", "What is the capital of Japan?"),
    ("factual", "What is the largest planet in our solar system?"),
    ("factual", "In what year did World War II end?"),
    ("factual", "What is the chemical symbol for sodium?"),
    ("factual", "Who painted the Mona Lisa?"),
    ("factual", "What is the tallest mountain on Earth?"),
    # ---- math (single answer) ----
    ("math", "What is 48 divided by 6?"),
    ("math", "What is the square root of 144?"),
    ("math", "If a rectangle is 8 cm long and 5 cm wide, what is its area?"),
    ("math", "What is 15 percent of 200?"),
    ("math", "What is the next number in the sequence 2, 4, 8, 16?"),
    ("math", "Solve for x: 3x + 9 = 24."),
    # ---- instruction-following (constrained) ----
    ("instruction", "List the two days of the weekend, separated by commas."),
    ("instruction", "Convert the word 'run' to its past tense."),
    ("instruction", "Write the number forty-two in Roman numerals."),
    ("instruction", "Give the plural form of the word 'child'."),
    ("instruction", "Capitalize every word in this phrase: the quick brown fox."),
    ("instruction", "State the opposite of the direction 'north'."),
    # ---- ambiguous / underspecified (higher diversity) ----
    ("ambiguous", "Should I take the job?"),
    ("ambiguous", "How long will it take?"),
    ("ambiguous", "Where should we go?"),
    ("ambiguous", "Is this a good idea?"),
    ("ambiguous", "What time works for you?"),
    ("ambiguous", "Can you fix it?"),
    # ---- open-ended creative (high diversity) ----
    ("creative", "Write the first sentence of a science fiction story."),
    ("creative", "Invent a name for a cozy coffee shop and describe its vibe."),
    ("creative", "Describe the taste of a fruit that has never existed."),
    ("creative", "Compose a two-line poem about the ocean at night."),
    ("creative", "Imagine a new holiday and explain how people celebrate it."),
    ("creative", "Design a creature that lives in the clouds and describe it."),
]
assert len(PROMPTS) == 30, f"expected 30 prompts, got {len(PROMPTS)}"
# sanity: none of the pilot prompts is a spike prompt (disjoint sets)
_SPIKE = {
    "What is the capital of France?", "How many continents are there on Earth?",
    "What year did the Apollo 11 mission land on the Moon?",
    "What is the chemical symbol for gold?", "Who wrote the play 'Romeo and Juliet'?",
    "What is 17 multiplied by 23?",
    "If a train travels 60 km in 45 minutes, what is its average speed in km/h?",
    "What is the derivative of x^3 with respect to x?",
    "Compute the sum of the first 10 positive integers.",
    "List three primary colors, separated by commas.",
    "Rewrite this sentence in the past tense: 'She walks to the store.'",
    "Translate the word 'hello' into Spanish.", "Give a one-word antonym for 'hot'.",
    "Is it going to rain tomorrow?", "What should I have for dinner?", "Which is better?",
    "What does this mean?", "Write the opening line of a mystery novel.",
    "Describe an imaginary color that does not exist.",
    "Invent a name for a new planet and say one thing about it.",
}
assert not (_SPIKE & {p for _, p in PROMPTS}), "pilot prompt collides with a spike prompt"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def head_logits(model, h):
    """Apply the model's output head to a post-final-norm hidden state `h`.

    Mirrors mlx_lm Qwen2 Model.__call__ exactly, so these logits come from the SAME forward pass
    that produced the probe input vector (the head reads that exact hidden state). Verified in the
    spike: top-1 identical to the full forward pass for all 20 prompts, max abs logit diff 0.03.
    """
    if getattr(model.args, "tie_word_embeddings", False):
        return model.model.embed_tokens.as_linear(h)
    return model.lm_head(h)


def next_token_entropy_nats(logits_1v):
    """Shannon entropy (natural log / nats) of the next-token distribution.

    `logits_1v` is an mlx array of shape (1, vocab) — the head output at the last prompt token.
    Softmax and entropy are computed in float32 numpy (fp16 activation cast to fp32, per e3-0001).
    """
    z = np.asarray(logits_1v[0], dtype=np.float32)
    z = z - z.max()
    ez = np.exp(z)
    p = ez / ez.sum()
    nz = p[p > 0.0]
    return float(-(nz * np.log(nz)).sum())


def eos_id_set(tokenizer):
    ids = set()
    tid = getattr(tokenizer, "eos_token_ids", None)
    if tid:
        ids |= {int(t) for t in tid}
    tid2 = getattr(tokenizer, "eos_token_id", None)
    if tid2 is not None:
        ids.add(int(tid2))
    return ids


def generate_text(model, tokenizer, prompt_ids, sampler, max_tokens, eos_ids, seed=None):
    """Generate one continuation. Early EOS kept (breaks and excludes the EOS token from text).

    Returns (text, n_tokens, eos_hit, wall_s).
    """
    if seed is not None:
        mx.random.seed(seed)
    prompt_arr = mx.array(prompt_ids)
    toks = []
    eos_hit = False
    t0 = time.perf_counter()
    for token, _logprobs in generate_step(
        prompt_arr, model, max_tokens=max_tokens, sampler=sampler
    ):
        t = int(token)
        if t in eos_ids:
            eos_hit = True
            break
        toks.append(t)
    wall_s = time.perf_counter() - t0
    text = tokenizer.decode(toks) if toks else ""
    return text, len(toks), eos_hit, wall_s


def parse_first_int_0_100(text):
    """First integer in [0, 100] appearing in `text` (e3-0003 parse rule). None if none."""
    num = ""
    for ch in text:
        if ch.isdigit():
            num += ch
        else:
            if num:
                v = int(num)
                if 0 <= v <= 100:
                    return v
                # keep scanning: a >100 run is not a valid confidence, look for the next integer
                num = ""
            else:
                num = ""
    if num:
        v = int(num)
        if 0 <= v <= 100:
            return v
    return None


def verbalized_confidence(model, tokenizer, task_prompt, greedy_sampler, eos_ids):
    """B1 two-turn verbalized confidence, greedy, first-int-0-100 parse, one identical retry.

    Returns a dict with the parsed value (or None), both raw turns, and bookkeeping flags.
    """
    t0 = time.perf_counter()
    # turn 1 — the model answers the task prompt (greedy)
    msgs1 = [{"role": "user", "content": task_prompt}]
    ids1 = tokenizer.apply_chat_template(msgs1, add_generation_prompt=True, tokenize=True)
    answer, ans_tokens, _ans_eos, _ = generate_text(
        model, tokenizer, ids1, greedy_sampler, MAX_TOKENS, eos_ids, seed=None
    )
    # turn 2 — ask for confidence with the frozen verbatim elicitation (greedy)
    msgs2 = [
        {"role": "user", "content": task_prompt},
        {"role": "assistant", "content": answer},
        {"role": "user", "content": VC_ELICITATION},
    ]
    ids2 = tokenizer.apply_chat_template(msgs2, add_generation_prompt=True, tokenize=True)
    conf_raw, _c_tok, _c_eos, _ = generate_text(
        model, tokenizer, ids2, greedy_sampler, 64, eos_ids, seed=None
    )
    value = parse_first_int_0_100(conf_raw)
    retried = False
    conf_raw_retry = None
    if value is None:
        # one identical retry (same prompt, same greedy decode)
        retried = True
        conf_raw_retry, _r_tok, _r_eos, _ = generate_text(
            model, tokenizer, ids2, greedy_sampler, 64, eos_ids, seed=None
        )
        value = parse_first_int_0_100(conf_raw_retry)
    return {
        "value": value,
        "missing": value is None,
        "parse_failed_first": parse_first_int_0_100(conf_raw) is None,
        "retried": retried,
        "answer": answer,
        "answer_tokens": ans_tokens,
        "conf_raw": conf_raw,
        "conf_raw_retry": conf_raw_retry,
        "elicitation_verbatim": VC_ELICITATION,
        "wall_s": time.perf_counter() - t0,
    }


def write_run_config(model, tokenizer):
    cfg = {
        "model_id": MODEL_ID,
        "model_revision_pinned": MODEL_REVISION,
        "mlx_version": mx.__version__,
        "python_version": sys.version.split()[0],
        "tie_word_embeddings": bool(getattr(model.args, "tie_word_embeddings", False)),
        "base_seed": BASE_SEED,
        "seed_formula": "base_seed + prompt_index * N + draw_index",
        "n_gen": N_GEN,
        "gen_temp": GEN_TEMP,
        "gen_top_p": GEN_TOP_P,
        "max_tokens": MAX_TOKENS,
        "nomic_model": NOMIC_MODEL,
        "nomic_revision_pinned": NOMIC_REVISION,
        "nomic_output_dim": NOMIC_DIM,
        "nomic_prefix": NOMIC_PREFIX,
        "nomic_prefix_decision_gap": (
            "nomic-embed v1.5 requires a task prefix; e3-0002 does not fix the choice. "
            "'clustering: ' used here as diversity/dispersion is the clustering-family use. "
            "Must be closed in the decision records before freeze."
        ),
        "vc_elicitation_verbatim": VC_ELICITATION,
        "entropy_base": ENTROPY_BASE,
        "volume_source": "e3_validation.volume.semantic_volume (e3-0002, called not reimplemented)",
        "n_prompts": len(PROMPTS),
    }
    try:
        import mlx_lm

        cfg["mlx_lm_version"] = mlx_lm.__version__
    except Exception:
        cfg["mlx_lm_version"] = "unknown"
    blob = json.dumps(cfg, sort_keys=True).encode()
    cfg["config_sha256"] = hashlib.sha256(blob).hexdigest()
    (RESULTS_DIR / "run_config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True))
    return cfg


def load_embedder():
    """Load nomic-embed-text-v1.5 on CPU, pinned revision, full 768-dim output."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        NOMIC_MODEL,
        revision=NOMIC_REVISION,
        trust_remote_code=True,
        device="cpu",
        truncate_dim=NOMIC_DIM,
    )


def atomic_write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print(f"[pilot] loading model {MODEL_ID} ...", flush=True)
    t_load = time.perf_counter()
    model, tokenizer = load(MODEL_ID)
    mx.eval(model.parameters())
    print(f"[pilot] model loaded in {time.perf_counter()-t_load:.2f}s", flush=True)

    eos_ids = eos_id_set(tokenizer)
    print(f"[pilot] eos ids = {sorted(eos_ids)}", flush=True)

    cfg = write_run_config(model, tokenizer)
    print(f"[pilot] config sha256 = {cfg['config_sha256']}", flush=True)

    sampler = make_sampler(temp=GEN_TEMP, top_p=GEN_TOP_P)
    greedy = make_sampler(temp=0.0)

    print(f"[pilot] loading embedder {NOMIC_MODEL}@{NOMIC_REVISION[:8]} ...", flush=True)
    t_emb = time.perf_counter()
    embedder = load_embedder()
    print(f"[pilot] embedder loaded in {time.perf_counter()-t_emb:.2f}s "
          f"(dim={embedder.get_sentence_embedding_dimension()})", flush=True)

    pilot_t0 = time.perf_counter()
    done, skipped = 0, 0
    for idx, (kind, prompt) in enumerate(PROMPTS):
        out_json = RESULTS_DIR / f"prompt_{idx:02d}.json"
        if out_json.exists():
            skipped += 1
            print(f"[prompt {idx:02d}] SKIP (exists) — {kind}", flush=True)
            continue

        t_prompt = time.perf_counter()

        # (1) extraction + entropy (one forward pass, no generation)
        messages = [{"role": "user", "content": prompt}]
        ids = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True
        )
        x = mx.array([ids])
        te = time.perf_counter()
        h_all = model.model(x)
        h_last = h_all[:, -1, :]  # (1, hidden) — pre-sampling state (e3-0001)
        mx.eval(h_last)
        extract_time_s = time.perf_counter() - te
        logits = head_logits(model, h_last)  # same forward pass -> B3 (e3-0003)
        mx.eval(logits)
        entropy = next_token_entropy_nats(logits)
        top1 = int(mx.argmax(logits, axis=-1).item())
        hidden_vec = np.array(h_last[0], dtype=np.float32)  # fp16 -> fp32 (e3-0001)

        # (2) N=10 seeded continuations (e3-0002)
        continuations = []
        texts = []
        gen_wall_0 = time.perf_counter()
        for d in range(N_GEN):
            seed = BASE_SEED + idx * N_GEN + d
            text, ntok, eos_hit, wall_s = generate_text(
                model, tokenizer, ids, sampler, MAX_TOKENS, eos_ids, seed=seed
            )
            texts.append(text)
            continuations.append({
                "draw": d, "seed": seed, "n_tokens": ntok,
                "eos_hit": eos_hit, "wall_s": wall_s, "text": text,
            })
        gen_total_wall_s = time.perf_counter() - gen_wall_0

        # (3) embed the 10 continuations + volume via the validation package
        t_e = time.perf_counter()
        emb = embedder.encode(
            [NOMIC_PREFIX + t for t in texts],
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        emb = np.asarray(emb, dtype=np.float32)
        embed_wall_s = time.perf_counter() - t_e
        volume = semantic_volume(emb)  # e3-0002 formula, CALLED not reimplemented

        # (4) B1 verbalized confidence (e3-0003)
        vc = verbalized_confidence(model, tokenizer, prompt, greedy, eos_ids)

        # persist hidden state + embeddings to npz (kept out of JSON to keep it lean)
        npz_path = RESULTS_DIR / f"prompt_{idx:02d}.npz"
        np.savez(
            npz_path,
            hidden_state=hidden_vec,
            continuation_embeddings=emb,
        )

        result = {
            "idx": idx,
            "kind": kind,
            "prompt": prompt,
            "throwaway": True,
            "prompt_tokens": len(ids),
            "hidden_dim": int(hidden_vec.shape[0]),
            "hidden_dtype_source": str(h_last.dtype),
            "next_token_entropy_nats": entropy,
            "entropy_base": ENTROPY_BASE,
            "top1_token_id": top1,
            "top1_token_str": tokenizer.decode([top1]),
            "extract_time_s": extract_time_s,
            "continuations": continuations,
            "realized_lengths": [c["n_tokens"] for c in continuations],
            "eos_hit_count": sum(c["eos_hit"] for c in continuations),
            "gen_total_wall_s": gen_total_wall_s,
            "embedding_model": NOMIC_MODEL,
            "embedding_revision": NOMIC_REVISION,
            "embedding_dim": int(emb.shape[1]),
            "embedding_prefix": NOMIC_PREFIX,
            "embed_wall_s": embed_wall_s,
            "semantic_volume": volume,
            "vc": vc,
            "npz": npz_path.name,
            "prompt_total_wall_s": time.perf_counter() - t_prompt,
        }
        atomic_write_json(out_json, result)
        done += 1
        print(
            f"[prompt {idx:02d}] {kind:11s} vol={volume:+.3f} ent={entropy:.3f} "
            f"vc={vc['value']} eos={result['eos_hit_count']}/{N_GEN} "
            f"len~{int(np.mean(result['realized_lengths']))} "
            f"t={result['prompt_total_wall_s']:.1f}s",
            flush=True,
        )

    print(
        f"[pilot] finished: {done} computed, {skipped} skipped, "
        f"wall {time.perf_counter()-pilot_t0:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
