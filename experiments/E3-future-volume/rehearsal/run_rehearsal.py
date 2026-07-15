"""
E3 LABELED dress rehearsal - the FULL E3 instrument end to end on ~40 THROWAWAY LABELED prompts.

Same per-prompt pipeline the pilot wired (pilot/run_pilot.py), reused verbatim in structure, with
two additions that make this a LABELED rehearsal rather than a plumbing pilot:

  (A) every prompt carries an intended-difficulty (1..4) and an author-verified GOLD, spanning
      three ANSWERABLE corpus families (arithmetic / factual / deduction). The three unanswerable
      corpus families (enumeration / creative) are deliberately absent - a rehearsal needs
      correctness labels on every item.
  (B) one dedicated GREEDY answer per prompt (temp 0.0) is generated and scored against the gold
      with the family-appropriate normalizer (normalizer.py, a concrete implementation of
      CORPUS.md § Labeling protocol). This greedy answer is SEPARATE from the 10 sampled
      continuations (which feed the volume) and separate in role from the verbalized-confidence
      turn-1 answer (though on a deterministic decode of the same prompt the two coincide; both
      are recorded).

Per prompt the pipeline is exactly the decision-record pipeline:
  (1) e3-0001 extraction: chat-template, one forward pass, no generation; hidden state
      model.model(ids)[:, -1, :] (fp16->fp32); B3 predictive entropy from the SAME forward pass.
  (2) e3-0002 ground truth: N=10 seeded continuations, temp 0.7 / top-p 0.95, 256 cap, early EOS
      kept. Seed per draw = base_seed + prompt_index * N + draw_index (base_seed = 20260714).
  (3) nomic-embed-text-v1.5 (pinned revision, dim 768, "clustering: " prefix - the SAME OPEN
      DECISION GAP the pilot flagged; e3-0002 does not fix the prefix) -> volume by CALLING
      e3_validation.volume.semantic_volume.
  (4) e3-0003 B1: two-turn verbalized confidence, frozen elicitation, greedy, first-int-0-100
      parse, one retry, missing counted.
  (5) NEW: greedy answer + normalizer correctness score.

DERIVED SEEDS (all off base_seed=20260714, documented for reproducibility):
  - continuation draw seed = base_seed + prompt_index * N_GEN + draw_index   (as pilot)
  - greedy decode is temperature 0 -> deterministic, no seed needed
  - the analysis seeds (split / bootstraps) live in analyze_rehearsal.py, also derived off base.

RESUMABLE: writes results/prompt_XX.json (+ .npz) incrementally, skips existing.

THROWAWAY DATA: the ~40 prompts are disposable rehearsal fodder. They MUST NEVER appear in, or
seed, the real E3 corpus. Disjointness from spike-20, pilot-30 and corpus-200 is asserted below
and quantified by disjointness.py (max token-set similarity reported in REHEARSAL.md).
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

import normalizer

# ---------------------------------------------------------------------------
# config (pins per e3-0002 / e3-0003 / e3-0004 - identical to the pilot)
# ---------------------------------------------------------------------------
MODEL_ID = "mlx-community/Qwen2.5-7B-Instruct-4bit"
MODEL_REVISION = "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed"

BASE_SEED = 20260714
N_GEN = 10
GEN_TEMP = 0.7
GEN_TOP_P = 0.95
MAX_TOKENS = 256

NOMIC_MODEL = "nomic-ai/nomic-embed-text-v1.5"
NOMIC_REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"
NOMIC_DIM = 768
NOMIC_PREFIX = "clustering: "  # SAME open decision gap the pilot flagged (e3-0002 does not fix it)

VC_ELICITATION = (
    "On a scale from 0 to 100, what is the probability that your answer above is correct? "
    "Reply with a single integer between 0 and 100 and nothing else."
)

ENTROPY_BASE = "nats"

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# ~40 THROWAWAY LABELED prompts. Fields: (kind, difficulty 1..4, prompt, gold).
# Families are the three ANSWERABLE corpus families. Difficulty is the rehearsal's 1..4 band:
#   1 trivial  (corpus d1-like)         2 medium (corpus d3-like)
#   3 hard     (the band corpus         4 very hard (the band corpus hardening would ADD -
#              hardening would add)                  genuinely hard but still single-answer)
# Golds are author-verified (arithmetic recomputed from scratch; factual single-canonical;
# deduction re-derived from premises). See REHEARSAL.md for the verification table.
# ---------------------------------------------------------------------------
PROMPTS = [
    # ===== ARITHMETIC (13) =====
    ("arithmetic", 1, "What is 9 times 8?", "72"),
    ("arithmetic", 1, "What is 63 divided by 7?", "9"),
    ("arithmetic", 1, "What is 47 plus 28?", "75"),
    ("arithmetic", 2, "What is 40 percent of 250?", "100"),
    ("arithmetic", 2, "What is 6 plus 7 times 8?", "62"),
    ("arithmetic", 2, "What is 2 to the power of 7?", "128"),
    ("arithmetic", 3, "A jacket costs 80 dollars and is discounted by 15 percent. What is the sale price in dollars?", "68"),
    ("arithmetic", 3, "A car travels 240 km using 8 liters of fuel. How many kilometers does it travel per liter?", "30"),
    ("arithmetic", 4, "A store sells pens at 3 for 2 dollars. How much do 12 pens cost in dollars?", "8"),
    ("arithmetic", 4, "A tank holds 800 liters and is 35 percent full. If 90 liters are added, how many liters are in it?", "370"),
    ("arithmetic", 4, "Tom is 3 times as old as Sara. In 4 years, Tom will be 28. How old is Sara now?", "8"),
    ("arithmetic", 4, "A worker earns 15 dollars per hour and works 7 hours a day for 5 days. What are the total earnings in dollars?", "525"),
    ("arithmetic", 3, "A rectangle has a perimeter of 36 cm and a width of 6 cm. What is its area in square centimeters?", "72"),
    # ===== FACTUAL (14) =====
    ("factual", 1, "What is the capital of Italy?", "Rome"),
    ("factual", 1, "How many months are there in a year?", "12"),
    ("factual", 1, "What color do you get by mixing blue and yellow?", "green"),
    ("factual", 1, "What is the capital of Spain?", "Madrid"),
    ("factual", 2, "What is the chemical symbol for oxygen?", "O"),
    ("factual", 2, "What planet is known as the Red Planet?", "Mars"),
    ("factual", 2, "What is the largest continent by area?", "Asia"),
    ("factual", 2, "What is the chemical symbol for carbon?", "C"),
    ("factual", 3, "What is the capital of Australia?", "Canberra"),
    ("factual", 3, "What is the chemical symbol for potassium?", "K"),
    ("factual", 3, "What is the chemical symbol for iron?", "Fe"),
    ("factual", 4, "What is the capital of Canada?", "Ottawa"),
    ("factual", 4, "What is the chemical symbol for tungsten?", "W"),
    ("factual", 4, "What is the smallest country in the world by area?", "Vatican City"),
    # ===== DEDUCTION (14) =====
    ("deduction", 1, "All birds have feathers. A robin is a bird. Does a robin have feathers? Answer yes or no.", "yes"),
    ("deduction", 1, "Maria is older than Tom. Who is younger, Maria or Tom?", "Tom"),
    ("deduction", 1, "A truck is heavier than a bicycle. Which one is lighter?", "bicycle"),
    ("deduction", 2, "Lee is taller than Max. Max is taller than Sam. Who is the tallest?", "Lee"),
    ("deduction", 2, "P finishes before Q. Q finishes before R. Who finishes first?", "P"),
    ("deduction", 2, "If yesterday was Friday, what day is tomorrow?", "Sunday"),
    ("deduction", 3, "Four runners finish a race. Kim beats Lou. Lou beats Max. Max beats Ned. Who finishes second?", "Lou"),
    ("deduction", 3, "Iron is denser than Wood. Foam is less dense than Wood. Stone is denser than Iron. Which of the four is the least dense?", "Foam"),
    ("deduction", 3, "Among four people, the manager earns more than the clerk, the clerk earns more than the guard, and the guard earns more than the intern. Who earns the most?", "manager"),
    ("deduction", 3, "On a shelf, the cup is above the bowl, and the bowl is above the plate. What is at the bottom?", "plate"),
    ("deduction", 3, "Ana is faster than Bea. Bea is faster than Cara. Cara is faster than Dana. Who is the slowest?", "Dana"),
    ("deduction", 4, "Five people sit in a row. Ann is to the left of Bob, Bob is to the left of Cara, Cara is to the left of Dan, and Dan is to the left of Eve. Who is in the middle?", "Cara"),
    ("deduction", 4, "There are four switches and exactly one is on. Switch A is off, Switch B is off, and Switch D is off. Which switch is on?", "C"),
    ("deduction", 4, "A is twice as old as B. B is 4 years older than C. C is 6 years old. How old is A?", "20"),
]

_KINDS = {"arithmetic", "factual", "deduction"}
assert all(k in _KINDS for k, _, _, _ in PROMPTS), "unexpected family"
assert all(1 <= d <= 4 for _, d, _, _ in PROMPTS), "difficulty out of 1..4"
assert len({p for _, _, p, _ in PROMPTS}) == len(PROMPTS), "duplicate prompt in rehearsal set"
print(f"[rehearsal] {len(PROMPTS)} labeled throwaway prompts loaded", file=sys.stderr)


# ---------------------------------------------------------------------------
# helpers (identical to the pilot's verified patterns)
# ---------------------------------------------------------------------------
def head_logits(model, h):
    if getattr(model.args, "tie_word_embeddings", False):
        return model.model.embed_tokens.as_linear(h)
    return model.lm_head(h)


def next_token_entropy_nats(logits_1v):
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
    if seed is not None:
        mx.random.seed(seed)
    prompt_arr = mx.array(prompt_ids)
    toks = []
    eos_hit = False
    t0 = time.perf_counter()
    for token, _lp in generate_step(prompt_arr, model, max_tokens=max_tokens, sampler=sampler):
        t = int(token)
        if t in eos_ids:
            eos_hit = True
            break
        toks.append(t)
    wall_s = time.perf_counter() - t0
    text = tokenizer.decode(toks) if toks else ""
    return text, len(toks), eos_hit, wall_s


def parse_first_int_0_100(text):
    num = ""
    for ch in text:
        if ch.isdigit():
            num += ch
        else:
            if num:
                v = int(num)
                if 0 <= v <= 100:
                    return v
                num = ""
            else:
                num = ""
    if num:
        v = int(num)
        if 0 <= v <= 100:
            return v
    return None


def greedy_answer(model, tokenizer, task_prompt, greedy_sampler, eos_ids):
    """One dedicated greedy answer to the task prompt (temp 0), for correctness scoring."""
    msgs = [{"role": "user", "content": task_prompt}]
    ids = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
    text, ntok, eos_hit, wall_s = generate_text(
        model, tokenizer, ids, greedy_sampler, MAX_TOKENS, eos_ids, seed=None
    )
    return {"answer": text, "n_tokens": ntok, "eos_hit": eos_hit, "wall_s": wall_s}


def verbalized_confidence(model, tokenizer, task_prompt, greedy_sampler, eos_ids):
    t0 = time.perf_counter()
    msgs1 = [{"role": "user", "content": task_prompt}]
    ids1 = tokenizer.apply_chat_template(msgs1, add_generation_prompt=True, tokenize=True)
    answer, ans_tokens, _e, _ = generate_text(
        model, tokenizer, ids1, greedy_sampler, MAX_TOKENS, eos_ids, seed=None
    )
    msgs2 = [
        {"role": "user", "content": task_prompt},
        {"role": "assistant", "content": answer},
        {"role": "user", "content": VC_ELICITATION},
    ]
    ids2 = tokenizer.apply_chat_template(msgs2, add_generation_prompt=True, tokenize=True)
    conf_raw, _c, _ce, _ = generate_text(model, tokenizer, ids2, greedy_sampler, 64, eos_ids, seed=None)
    value = parse_first_int_0_100(conf_raw)
    retried = False
    conf_raw_retry = None
    if value is None:
        retried = True
        conf_raw_retry, _r, _re, _ = generate_text(
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
            "'clustering: ' used, same as the pilot. Must be closed before freeze."
        ),
        "vc_elicitation_verbatim": VC_ELICITATION,
        "entropy_base": ENTROPY_BASE,
        "volume_source": "e3_validation.volume.semantic_volume (e3-0002, called not reimplemented)",
        "normalizer_source": "normalizer.py (concrete CORPUS.md § Labeling protocol impl)",
        "n_prompts": len(PROMPTS),
        "families": sorted(_KINDS),
        "difficulty_band": "1 trivial(d1-like) / 2 medium(d3-like) / 3 hard / 4 very-hard(hardening band)",
        "labeled_rehearsal": True,
        "throwaway": True,
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
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(
        NOMIC_MODEL, revision=NOMIC_REVISION, trust_remote_code=True,
        device="cpu", truncate_dim=NOMIC_DIM,
    )


def atomic_write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)


def main():
    print(f"[rehearsal] loading model {MODEL_ID} ...", flush=True)
    t_load = time.perf_counter()
    model, tokenizer = load(MODEL_ID)
    mx.eval(model.parameters())
    print(f"[rehearsal] model loaded in {time.perf_counter()-t_load:.2f}s", flush=True)

    eos_ids = eos_id_set(tokenizer)
    print(f"[rehearsal] eos ids = {sorted(eos_ids)}", flush=True)

    cfg = write_run_config(model, tokenizer)
    print(f"[rehearsal] config sha256 = {cfg['config_sha256']}", flush=True)

    sampler = make_sampler(temp=GEN_TEMP, top_p=GEN_TOP_P)
    greedy = make_sampler(temp=0.0)

    print(f"[rehearsal] loading embedder {NOMIC_MODEL}@{NOMIC_REVISION[:8]} ...", flush=True)
    t_emb = time.perf_counter()
    embedder = load_embedder()
    print(f"[rehearsal] embedder loaded in {time.perf_counter()-t_emb:.2f}s", flush=True)

    reh_t0 = time.perf_counter()
    done, skipped = 0, 0
    for idx, (kind, difficulty, prompt, gold) in enumerate(PROMPTS):
        out_json = RESULTS_DIR / f"prompt_{idx:02d}.json"
        if out_json.exists():
            skipped += 1
            print(f"[prompt {idx:02d}] SKIP (exists) - {kind} d{difficulty}", flush=True)
            continue

        t_prompt = time.perf_counter()

        # (1) extraction + entropy (one forward pass, no generation)
        messages = [{"role": "user", "content": prompt}]
        ids = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=True)
        x = mx.array([ids])
        te = time.perf_counter()
        h_all = model.model(x)
        h_last = h_all[:, -1, :]
        mx.eval(h_last)
        extract_time_s = time.perf_counter() - te
        logits = head_logits(model, h_last)
        mx.eval(logits)
        entropy = next_token_entropy_nats(logits)
        top1 = int(mx.argmax(logits, axis=-1).item())
        hidden_vec = np.array(h_last[0], dtype=np.float32)

        # (2) N=10 seeded continuations
        continuations, texts = [], []
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

        # e3-0002 exclusion bookkeeping: a continuation is valid iff non-empty after strip.
        # (refusal-pattern check is a no-op on these benign prompts; recorded for parity.)
        n_valid = sum(1 for t in texts if t.strip())
        excluded = n_valid < N_GEN

        # (3) embed + volume via the validation package
        t_e = time.perf_counter()
        emb = embedder.encode(
            [NOMIC_PREFIX + t for t in texts],
            convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=False,
        )
        emb = np.asarray(emb, dtype=np.float32)
        embed_wall_s = time.perf_counter() - t_e
        volume = semantic_volume(emb)

        # (4) B1 verbalized confidence
        vc = verbalized_confidence(model, tokenizer, prompt, greedy, eos_ids)

        # (5) dedicated greedy answer + correctness score
        ga = greedy_answer(model, tokenizer, prompt, greedy, eos_ids)
        is_correct, extracted, norm_note = normalizer.score(kind, ga["answer"], gold)

        npz_path = RESULTS_DIR / f"prompt_{idx:02d}.npz"
        np.savez(npz_path, hidden_state=hidden_vec, continuation_embeddings=emb)

        result = {
            "idx": idx,
            "kind": kind,
            "family": kind,
            "difficulty": difficulty,
            "prompt": prompt,
            "gold": gold,
            "throwaway": True,
            "answerable": True,
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
            "n_valid_continuations": n_valid,
            "excluded": excluded,
            "embedding_model": NOMIC_MODEL,
            "embedding_revision": NOMIC_REVISION,
            "embedding_dim": int(emb.shape[1]),
            "embedding_prefix": NOMIC_PREFIX,
            "embed_wall_s": embed_wall_s,
            "semantic_volume": volume,
            "vc": vc,
            "greedy_answer": ga["answer"],
            "greedy_answer_tokens": ga["n_tokens"],
            "greedy_answer_eos_hit": ga["eos_hit"],
            "correct": bool(is_correct),
            "normalizer_extracted": extracted,
            "normalizer_note": norm_note,
            "greedy_matches_vc_turn1": ga["answer"] == vc["answer"],
            "npz": npz_path.name,
            "prompt_total_wall_s": time.perf_counter() - t_prompt,
        }
        atomic_write_json(out_json, result)
        done += 1
        print(
            f"[prompt {idx:02d}] {kind:10s} d{difficulty} vol={volume:+.3f} ent={entropy:.3f} "
            f"vc={vc['value']} correct={int(is_correct)} gold={gold!r} "
            f"got={extracted!r} t={result['prompt_total_wall_s']:.1f}s",
            flush=True,
        )

    print(
        f"[rehearsal] finished: {done} computed, {skipped} skipped, "
        f"wall {time.perf_counter()-reh_t0:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
