"""
E3 CONFIRMATORY RUN — the full frozen E3 instrument, end to end, on the 200-prompt confirmatory
corpus (../corpus/candidates.jsonl). Resumable, seeded, revision-enforced, no remote APIs.

The per-prompt pipeline is the proven pilot/rehearsal pipeline (../pilot/run_pilot.py,
../rehearsal/run_rehearsal.py), reused verbatim in structure, with the frozen confirmatory contract:

  (1) e3-0001 extraction: chat-template, ONE forward pass, no generation; hidden state
      model.model(ids)[:, -1, :] (fp16 -> fp32); B3 naive predictive entropy (nats) from the SAME
      forward pass (head applied to that exact hidden state).
  (2) e3-0002 ground truth: N=10 seeded continuations, temp 0.7 / top-p 0.95, cap 256, early EOS
      kept. Seed per draw = base_seed + prompt_index * N + draw_index (base_seed = 20260714).
      A continuation is VALID iff, after strip, it is non-empty AND not a refusal (frozen anchored
      pattern list). Refusals are COUNTED, never resampled; a prompt with < 10 valid is flagged
      excluded (dropped downstream), volume still recorded for the audit trail.
  (3) nomic-embed-text-v1.5 (pinned revision, dim 768, "clustering: " prefix, CPU) -> semantic
      volume by CALLING e3_validation.volume.semantic_volume (e3-0002).
  (4) ANSWERABLE prompts only: one dedicated GREEDY answer (temp 0, cap 768 per HARDENING.md /
      e3-0005) scored against gold by the improved normalizer (hardening/improved_normalizer.py,
      frozen F1-F5b spec). Truncated (non-EOS) replies are flagged and excluded, never scored wrong.
  (5) ANSWERABLE prompts only: B1 verbalized confidence, BOTH frozen variants recorded:
        - zero_shot : frozen verbatim elicitation (e3-0003), greedy, first-int-0-100 parse, one
                      identical retry, missing counted.
        - cot       : chain-of-thought confidence variant (e3-0005 / registration): the model
                      reasons before stating the integer; greedy, last-int-0-100 parse (the stated
                      value follows the reasoning), one identical retry, missing counted.
      Both are zero-shot (no fine-tuning); the added-value gate uses the max over variants.
      The turn-1 answer is the SAME greedy answer as (4) (greedy decode of the same prompt), so the
      two coincide by construction and the shared answer is reused, not re-decoded.

Model loaded WITH revision enforcement via e3_validation.loader.load (fails closed unless the
resolved local snapshot equals the pin c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed) and the chat-
template hash is recorded. The embedder revision is pinned at load.

Before the first prompt: results/run_manifest.json is written — the full frozen config via
e3_validation.freeze.FrozenConfig (all thresholds at the operator-approved THRESHOLDS-PROPOSAL
values, all seeds/pins, corpus SHA-256, golds SHA-256, normalizer version, refusal list) plus the
registration status and start timestamp — and its committed SHA-256 is printed.

RESUMABLE: writes results/prompt_XXX.json (+ prompt_XXX.npz) per prompt and skips any whose JSON
already exists, so the run can be stopped and resumed touching nothing.
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# HF cache offline — no remote APIs (models + embedder are pinned in the local cache).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import mlx.core as mx
import numpy as np
import mlx_lm
from mlx_lm.generate import generate_step
from mlx_lm.sample_utils import make_sampler

from e3_validation.volume import semantic_volume, EPSILON
from e3_validation import loader as e3_loader
from e3_validation.freeze import (
    FrozenConfig,
    SamplerConfig,
    SeedConfig,
    ModelConfig,
    LibraryVersions,
)
from e3_validation.verdict import VerdictThresholds

# improved normalizer lives in ../hardening (frozen F1-F5b spec). Import it read-only.
HARDENING_DIR = Path(__file__).resolve().parent.parent / "hardening"
sys.path.insert(0, str(HARDENING_DIR))
import improved_normalizer  # noqa: E402

# ---------------------------------------------------------------------------
# frozen pins (e3-0002 / e3-0003 / e3-0004 / e3-0005)
# ---------------------------------------------------------------------------
MODEL_ID = "mlx-community/Qwen2.5-7B-Instruct-4bit"
MODEL_REVISION = "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed"

BASE_SEED = 20260714
N_GEN = 10
GEN_TEMP = 0.7
GEN_TOP_P = 0.95
MAX_TOKENS = 256          # continuation cap (e3-0002)
ANSWER_CAP = 768          # correctness / VC turn-1 greedy answer cap (HARDENING.md / e3-0005)
CONF_CAP_ZERO_SHOT = 64   # confidence-utterance cap, zero-shot (short integer reply)
CONF_CAP_COT = 512        # confidence-utterance cap, CoT variant (reasoning + integer)

NOMIC_MODEL = "nomic-ai/nomic-embed-text-v1.5"
NOMIC_REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"
NOMIC_DIM = 768
NOMIC_PREFIX = "clustering: "

ENTROPY_BASE = "nats"

# B1 zero-shot elicitation — FROZEN VERBATIM (e3-0003; registration § 2).
VC_ELICITATION_ZERO_SHOT = (
    "On a scale from 0 to 100, what is the probability that your answer above is correct? "
    "Reply with a single integer between 0 and 100 and nothing else."
)
# B1 chain-of-thought variant — FROZEN VERBATIM (e3-0005 / registration: reasons before the integer).
VC_ELICITATION_COT = (
    "Think step by step about whether your answer above is correct. "
    "After your reasoning, on the final line state the probability that your answer above is "
    "correct as a single integer between 0 and 100."
)

# Refusal-pattern list — FROZEN, anchored, case-insensitive leading patterns (e3-0005; registration
# § 3). A reply is a refusal iff, after whitespace strip, it matches any of these at the start.
REFUSAL_PATTERNS = (
    r"^\s*I can'?t",
    r"^\s*I cannot",
    r"^\s*I'?m unable",
    r"^\s*I won'?t",
)
_REFUSAL_RE = [re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS]

# Normalizer spec version (frozen F1-F5b, HARDENING.md; self-check 27/27).
NORMALIZER_SPEC_VERSION = "improved_normalizer/F1-F5b@hardening/HARDENING.md"

# Operator-approved verdict thresholds (THRESHOLDS-PROPOSAL.md primary values; e3-0005 open set).
THRESHOLDS = VerdictThresholds(
    min_negatives=15,
    r2_fidelity_min=0.10,
    spearman_fidelity_min=0.3,
    within_family_spearman_min=0.3,
    family_oracle_margin_min=0.05,
    r2_margin_over_classmean_min=0.05,
    ood_pooled_spearman_min=0.2,
    ood_per_family_floor=0.0,
    auc_binary_min=0.70,
    vc_ci_floor=0.0,
    b3_ci_floor=0.0,
    b4_margin_ceiling=0.0,
    require_length_robust=True,
)

# Analysis-stage params recorded in the freeze (this run produces per-prompt data; the probe/verdict
# analysis is downstream, but its result-moving inputs are frozen here per e3-0004 / THRESHOLDS).
ALPHA_GRID = tuple(float(a) for a in np.logspace(-2, 6, 9))  # decade grid 1e-2 .. 1e6, 9 points
INNER_CV_FOLDS = 5
CORRECTNESS_CV_FOLDS = 5
BOOTSTRAP_N = 10000
BOOTSTRAP_CI_LEVEL = 0.95
TEST_FRACTION = 0.2  # n=200 -> 160 train / 40 held-out in-distribution (THRESHOLDS-PROPOSAL)

REGISTRATION_STATUS = (
    "none — run ordered by operator 2026-07-15, pre-registration waived"
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CORPUS_PATH = Path(__file__).resolve().parent.parent / "corpus" / "candidates.jsonl"


# ---------------------------------------------------------------------------
# helpers (pilot/rehearsal verified patterns, reused verbatim)
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
    """One continuation. Early EOS kept (breaks, excludes EOS from text). Returns text, n, eos, wall."""
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


def is_refusal(text):
    """Frozen refusal check: matches any anchored leading pattern after whitespace strip."""
    s = text.strip()
    return any(rx.match(s) for rx in _REFUSAL_RE)


def _int_runs_0_100(text):
    """Yield every maximal digit run's integer value that falls in [0, 100], in order."""
    out = []
    for m in re.finditer(r"\d+", text):
        v = int(m.group(0))
        if 0 <= v <= 100:
            out.append(v)
    return out


def parse_first_int_0_100(text):
    """First integer in [0, 100] (e3-0003 zero-shot parse rule). None if none."""
    runs = _int_runs_0_100(text)
    return runs[0] if runs else None


def parse_last_int_0_100(text):
    """Last integer in [0, 100] — the CoT variant's stated value follows the reasoning."""
    runs = _int_runs_0_100(text)
    return runs[-1] if runs else None


def greedy_answer(model, tokenizer, task_prompt, greedy_sampler, eos_ids):
    """One dedicated greedy answer (temp 0, cap ANSWER_CAP) for correctness scoring + VC turn-1."""
    msgs = [{"role": "user", "content": task_prompt}]
    ids = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
    text, ntok, eos_hit, wall_s = generate_text(
        model, tokenizer, ids, greedy_sampler, ANSWER_CAP, eos_ids, seed=None
    )
    return {"answer": text, "n_tokens": ntok, "eos_hit": eos_hit, "wall_s": wall_s}


def verbalized_confidence(model, tokenizer, task_prompt, answer, elicitation, parse_fn,
                          conf_cap, greedy_sampler, eos_ids):
    """B1 turn-2 confidence, greedy, one identical retry, missing counted. Turn-1 `answer` reused."""
    t0 = time.perf_counter()
    msgs2 = [
        {"role": "user", "content": task_prompt},
        {"role": "assistant", "content": answer},
        {"role": "user", "content": elicitation},
    ]
    ids2 = tokenizer.apply_chat_template(msgs2, add_generation_prompt=True, tokenize=True)
    conf_raw, _c, _ce, _ = generate_text(
        model, tokenizer, ids2, greedy_sampler, conf_cap, eos_ids, seed=None
    )
    value = parse_fn(conf_raw)
    retried = False
    conf_raw_retry = None
    if value is None:
        retried = True
        conf_raw_retry, _r, _re, _ = generate_text(
            model, tokenizer, ids2, greedy_sampler, conf_cap, eos_ids, seed=None
        )
        value = parse_fn(conf_raw_retry)
    return {
        "value": value,
        "missing": value is None,
        "parse_failed_first": parse_fn(conf_raw) is None,
        "retried": retried,
        "conf_raw": conf_raw,
        "conf_raw_retry": conf_raw_retry,
        "elicitation_verbatim": elicitation,
        "wall_s": time.perf_counter() - t0,
    }


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


def sha256_file(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def load_corpus():
    items = []
    for line in Path(CORPUS_PATH).read_text().splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


# ---------------------------------------------------------------------------
# revision-enforced model load (e3_validation.loader.load, fail-closed)
# ---------------------------------------------------------------------------
_LOADED = {}


def _loader_fn(model_id, revision):
    """loader_fn for e3_validation.loader.load: resolve the pinned LOCAL snapshot, load from it,
    return (resolved_revision, render_chat). Fails closed if the pinned snapshot is absent (offline).
    """
    from huggingface_hub import snapshot_download
    snap = snapshot_download(model_id, revision=revision, local_files_only=True)
    resolved = Path(snap).resolve().name  # snapshots/<commit>/ -> commit hash
    model, tokenizer = mlx_lm.load(snap)
    mx.eval(model.parameters())
    _LOADED["model"] = model
    _LOADED["tokenizer"] = tokenizer

    def render_chat(messages):
        return tokenizer.apply_chat_template(
            list(messages), add_generation_prompt=True, tokenize=False
        )

    return resolved, render_chat


def build_frozen_config(corpus_items, hidden_dim, eos_id, chat_template_sha):
    corpus_sha = sha256_file(CORPUS_PATH)
    golds_blob = json.dumps(
        {it["id"]: it.get("gold") for it in corpus_items}, sort_keys=True
    ).encode("utf-8")
    golds_sha = hashlib.sha256(golds_blob).hexdigest()

    import numpy as _np
    import sklearn as _sk
    import scipy as _sp

    cfg = FrozenConfig(
        corpus_sha256=corpus_sha,
        golds_sha256=golds_sha,
        refusal_regexes=REFUSAL_PATTERNS,
        normalizer_spec_version=NORMALIZER_SPEC_VERSION,
        epsilon=EPSILON,
        n_continuations=N_GEN,
        sampler=SamplerConfig(
            temperature=GEN_TEMP, top_p=GEN_TOP_P, max_tokens=MAX_TOKENS, eos_id=eos_id
        ),
        seeds=SeedConfig(base_seed=BASE_SEED),
        alpha_grid=ALPHA_GRID,
        inner_cv_folds=INNER_CV_FOLDS,
        correctness_cv_folds=CORRECTNESS_CV_FOLDS,
        bootstrap_n=BOOTSTRAP_N,
        bootstrap_ci_level=BOOTSTRAP_CI_LEVEL,
        test_fraction=TEST_FRACTION,
        thresholds=THRESHOLDS,
        model=ModelConfig(
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            tokenizer_revision=MODEL_REVISION,
            chat_template_sha256=chat_template_sha,
            hidden_dim=hidden_dim,
            embedder_id=NOMIC_MODEL,
            embedder_revision=NOMIC_REVISION,
            embedder_prefix=NOMIC_PREFIX,
            embedder_dim=NOMIC_DIM,
        ),
        libraries=LibraryVersions(
            python=sys.version.split()[0],
            numpy=_np.__version__,
            scikit_learn=_sk.__version__,
            scipy=_sp.__version__,
            mlx_lm=mlx_lm.__version__,
        ),
    )
    return cfg


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print(f"[run] HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE')}", flush=True)
    print(f"[run] loading {MODEL_ID}@{MODEL_REVISION[:8]} with revision enforcement ...", flush=True)
    t_load = time.perf_counter()
    loaded = e3_loader.load(MODEL_ID, MODEL_REVISION, _loader_fn)
    model, tokenizer = _LOADED["model"], _LOADED["tokenizer"]
    print(f"[run] model loaded in {time.perf_counter()-t_load:.2f}s | resolved="
          f"{loaded.resolved_revision[:8]} chat_template_sha={loaded.chat_template_sha256[:12]}",
          flush=True)

    eos_ids = eos_id_set(tokenizer)
    eos_primary = int(getattr(tokenizer, "eos_token_id", sorted(eos_ids)[0]))
    hidden_dim = int(model.args.hidden_size)
    print(f"[run] eos ids = {sorted(eos_ids)} (primary {eos_primary}) | hidden_dim = {hidden_dim}",
          flush=True)

    corpus = load_corpus()
    print(f"[run] corpus: {len(corpus)} prompts "
          f"({sum(1 for it in corpus if it.get('answerable'))} answerable)", flush=True)

    # --- frozen manifest (before the first prompt) ---
    cfg = build_frozen_config(corpus, hidden_dim, eos_primary, loaded.chat_template_sha256)
    cfg_hash = cfg.sha256()
    manifest = {
        "frozen_config": cfg.to_dict(),
        "frozen_config_sha256": cfg_hash,
        "registration": REGISTRATION_STATUS,
        "start_timestamp": datetime.now(timezone.utc).isoformat(),
        "loaded_model": {
            "model_id": loaded.model_id,
            "requested_revision": loaded.requested_revision,
            "resolved_revision": loaded.resolved_revision,
            "chat_template_sha256": loaded.chat_template_sha256,
        },
        "corpus_path": str(CORPUS_PATH),
        "n_prompts": len(corpus),
        "n_answerable": sum(1 for it in corpus if it.get("answerable")),
        "answer_cap_correctness": ANSWER_CAP,
        "continuation_eos_ids": sorted(eos_ids),
        "entropy_base": ENTROPY_BASE,
        "volume_source": "e3_validation.volume.semantic_volume (e3-0002, called not reimplemented)",
        "normalizer_source": (
            "hardening/improved_normalizer.py (frozen F1-F5b spec; score(item, answer, eos_hit))"
        ),
        "refusal_patterns_verbatim": list(REFUSAL_PATTERNS),
        "b1_variants": {
            "zero_shot": {
                "elicitation_verbatim": VC_ELICITATION_ZERO_SHOT,
                "parse_rule": "first-integer-in-[0,100]",
                "conf_cap": CONF_CAP_ZERO_SHOT,
                "retry": "one identical retry on parse failure",
                "missing": "counted",
                "frozen_by": "e3-0003 (verbatim); registration § 2",
            },
            "cot": {
                "elicitation_verbatim": VC_ELICITATION_COT,
                "parse_rule": "last-integer-in-[0,100] (stated value follows the reasoning)",
                "conf_cap": CONF_CAP_COT,
                "retry": "one identical retry on parse failure",
                "missing": "counted",
                "frozen_by": "e3-0005 / registration § 2 (chain-of-thought confidence variant)",
            },
            "added_value_gate": "max over verbalized variants (e3-0005; both zero-shot)",
        },
        "seed_formula_continuation": "base_seed + prompt_index * N + draw_index",
        "resumable": "skips any prompt whose results/prompt_XXX.json already exists",
    }
    atomic_write_json(RESULTS_DIR / "run_manifest.json", manifest)
    print(f"[run] MANIFEST written: results/run_manifest.json", flush=True)
    print(f"[run] FROZEN CONFIG SHA-256 = {cfg_hash}", flush=True)

    sampler = make_sampler(temp=GEN_TEMP, top_p=GEN_TOP_P)
    greedy = make_sampler(temp=0.0)

    print(f"[run] loading embedder {NOMIC_MODEL}@{NOMIC_REVISION[:8]} (CPU) ...", flush=True)
    t_emb = time.perf_counter()
    embedder = load_embedder()
    print(f"[run] embedder loaded in {time.perf_counter()-t_emb:.2f}s "
          f"(dim={embedder.get_sentence_embedding_dimension()})", flush=True)

    run_t0 = time.perf_counter()
    done, skipped = 0, 0
    for idx, item in enumerate(corpus):
        cid = item["id"]
        family = item["family"]
        prompt = item["prompt"]
        answerable = bool(item.get("answerable"))
        gold = item.get("gold")

        out_json = RESULTS_DIR / f"prompt_{idx:03d}.json"
        if out_json.exists():
            skipped += 1
            print(f"[{idx:03d} {cid}] SKIP (exists)", flush=True)
            continue

        t_prompt = time.perf_counter()

        # (1) extraction + entropy — one forward pass, no generation
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

        # (2) N=10 seeded continuations, refusal-counted
        continuations, texts = [], []
        for d in range(N_GEN):
            seed = BASE_SEED + idx * N_GEN + d
            text, ntok, eos_hit, wall_s = generate_text(
                model, tokenizer, ids, sampler, MAX_TOKENS, eos_ids, seed=seed
            )
            texts.append(text)
            refusal = is_refusal(text)
            continuations.append({
                "draw": d, "seed": seed, "n_tokens": ntok, "eos_hit": eos_hit,
                "wall_s": wall_s, "refusal": refusal, "text": text,
            })
        n_refusals = sum(1 for c in continuations if c["refusal"])
        n_valid = sum(1 for c in continuations if c["text"].strip() and not c["refusal"])
        excluded = n_valid < N_GEN

        # (3) embed + volume via the validation package (all N; excluded flag carries the caveat)
        t_e = time.perf_counter()
        emb = embedder.encode(
            [NOMIC_PREFIX + t for t in texts],
            convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=False,
        )
        emb = np.asarray(emb, dtype=np.float32)
        embed_wall_s = time.perf_counter() - t_e
        volume = semantic_volume(emb)

        result = {
            "idx": idx,
            "id": cid,
            "family": family,
            "kind": family,
            "difficulty": item.get("difficulty"),
            "expected_diversity": item.get("expected_diversity"),
            "prompt": prompt,
            "answerable": answerable,
            "gold": gold,
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
            "n_refusals": n_refusals,
            "n_valid_continuations": n_valid,
            "excluded": excluded,
            "embedding_model": NOMIC_MODEL,
            "embedding_revision": NOMIC_REVISION,
            "embedding_dim": int(emb.shape[1]),
            "embedding_prefix": NOMIC_PREFIX,
            "embed_wall_s": embed_wall_s,
            "semantic_volume": volume,
        }

        # (4)+(5) answerable only: greedy answer + correctness + both B1 variants
        if answerable:
            ga = greedy_answer(model, tokenizer, prompt, greedy, eos_ids)
            sr = improved_normalizer.score(item, ga["answer"], ga["eos_hit"])
            vc_zero = verbalized_confidence(
                model, tokenizer, prompt, ga["answer"], VC_ELICITATION_ZERO_SHOT,
                parse_first_int_0_100, CONF_CAP_ZERO_SHOT, greedy, eos_ids,
            )
            vc_zero["parse_rule"] = "first-integer-in-[0,100]"
            vc_cot = verbalized_confidence(
                model, tokenizer, prompt, ga["answer"], VC_ELICITATION_COT,
                parse_last_int_0_100, CONF_CAP_COT, greedy, eos_ids,
            )
            vc_cot["parse_rule"] = "last-integer-in-[0,100]"
            result.update({
                "greedy_answer": ga["answer"],
                "greedy_answer_tokens": ga["n_tokens"],
                "greedy_answer_eos_hit": ga["eos_hit"],
                "correct": bool(sr.is_correct),
                "normalizer_extracted": sr.extracted,
                "normalizer_note": sr.note,
                "normalizer_truncated": bool(sr.truncated),
                "vc_zero_shot": vc_zero,
                "vc_cot": vc_cot,
                "greedy_is_vc_turn1": True,
            })
        else:
            result.update({
                "greedy_answer": None,
                "correct": None,
                "vc_zero_shot": None,
                "vc_cot": None,
            })

        npz_path = RESULTS_DIR / f"prompt_{idx:03d}.npz"
        np.savez(npz_path, hidden_state=hidden_vec, continuation_embeddings=emb)
        result["npz"] = npz_path.name
        result["prompt_total_wall_s"] = time.perf_counter() - t_prompt

        atomic_write_json(out_json, result)
        done += 1
        if answerable:
            print(
                f"[{idx:03d} {cid:10s}] {family:10s} vol={volume:+.3f} ent={entropy:.3f} "
                f"correct={int(result['correct'])} vcz={result['vc_zero_shot']['value']} "
                f"vcc={result['vc_cot']['value']} valid={n_valid}/{N_GEN} "
                f"t={result['prompt_total_wall_s']:.1f}s",
                flush=True,
            )
        else:
            print(
                f"[{idx:03d} {cid:10s}] {family:10s} vol={volume:+.3f} ent={entropy:.3f} "
                f"(open) valid={n_valid}/{N_GEN} eos={result['eos_hit_count']}/{N_GEN} "
                f"t={result['prompt_total_wall_s']:.1f}s",
                flush=True,
            )

    print(
        f"[run] finished: {done} computed, {skipped} skipped, "
        f"wall {time.perf_counter()-run_t0:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
