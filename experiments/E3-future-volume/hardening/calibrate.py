"""
E3 hardening CALIBRATION runner -- Qwen2.5-7B-Instruct-4bit greedy on DISPOSABLE candidate hard
prompts, scored with improved_normalizer, to measure per-KIND accuracy and find the kinds that sit
in the 30-80% band (REHEARSAL.md: hardening must change KIND, not degree).

Reuses the rehearsal's generation machinery VERBATIM in structure (run_rehearsal.py greedy path):
same model id + pinned revision, same chat template, same greedy sampler (temp 0), same EOS
handling. The ONLY intentional differences from the rehearsal greedy answer:
  (1) answer token cap raised 256 -> 640 so a completed chain-of-thought is not truncated
      (improved_normalizer F1 -- the rehearsal's single "negative" was a 256-cap truncation);
  (2) scoring goes through improved_normalizer (F1-F5 fixes) instead of normalizer.py;
  (3) no volume / hidden-state / verbalized-confidence -- calibration only needs correctness.

Determinism: greedy decode (temp 0) is deterministic; no seed needed (identical to the rehearsal's
greedy answer). Model revision pinned. Resumable: per-item JSON in calib_results/, existing skipped.

Usage:  uv run --project ../rehearsal python calibrate.py --rounds 1
        (any Python env with mlx-lm + the pinned model in the local HF cache works)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import mlx.core as mx
from mlx_lm import load
from mlx_lm.generate import generate_step
from mlx_lm.sample_utils import make_sampler

import improved_normalizer
from calib_prompts import ALL_ROUNDS, collect

MODEL_ID = "mlx-community/Qwen2.5-7B-Instruct-4bit"
MODEL_REVISION = "c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed"  # pinned, identical to the rehearsal
MAX_TOKENS = 640  # F1: raised from the rehearsal's 256 so completed CoT is not truncated

RESULTS_DIR = Path(__file__).resolve().parent / "calib_results"
RESULTS_DIR.mkdir(exist_ok=True)


def eos_id_set(tokenizer):
    ids = set()
    tid = getattr(tokenizer, "eos_token_ids", None)
    if tid:
        ids |= {int(t) for t in tid}
    tid2 = getattr(tokenizer, "eos_token_id", None)
    if tid2 is not None:
        ids.add(int(tid2))
    return ids


def generate_greedy(model, tokenizer, prompt, sampler, eos_ids):
    msgs = [{"role": "user", "content": prompt}]
    ids = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
    toks, eos_hit = [], False
    t0 = time.perf_counter()
    for token, _lp in generate_step(mx.array(ids), model, max_tokens=MAX_TOKENS, sampler=sampler):
        t = int(token)
        if t in eos_ids:
            eos_hit = True
            break
        toks.append(t)
    wall = time.perf_counter() - t0
    return tokenizer.decode(toks) if toks else "", len(toks), eos_hit, wall


def item_key(it):
    # stable filename per prompt (round + kind + short hash of the prompt)
    import hashlib
    h = hashlib.sha1(it["prompt"].encode()).hexdigest()[:10]
    return f"r{it['round']}_{it['kind']}_{h}"


def main():
    global MAX_TOKENS
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, nargs="+", default=[1])
    ap.add_argument("--max-tokens", type=int, default=640,
                    help="answer token cap (F1: >=640; raised for long 8-entity CoT in round 3)")
    args = ap.parse_args()
    MAX_TOKENS = args.max_tokens
    print(f"[calib] MAX_TOKENS={MAX_TOKENS}", flush=True)

    items = collect(sorted(set(args.rounds) & set(ALL_ROUNDS)))
    print(f"[calib] rounds={args.rounds}  {len(items)} disposable prompts", flush=True)

    print(f"[calib] loading {MODEL_ID} ...", flush=True)
    t_load = time.perf_counter()
    model, tokenizer = load(MODEL_ID)
    mx.eval(model.parameters())
    print(f"[calib] loaded in {time.perf_counter()-t_load:.1f}s", flush=True)
    eos_ids = eos_id_set(tokenizer)
    greedy = make_sampler(temp=0.0)

    t0 = time.perf_counter()
    for i, it in enumerate(items):
        out = RESULTS_DIR / f"{item_key(it)}.json"
        if out.exists():
            print(f"[{i:02d}] SKIP {it['kind']}", flush=True)
            continue
        answer, ntok, eos_hit, wall = generate_greedy(model, tokenizer, it["prompt"], greedy, eos_ids)
        res = improved_normalizer.score(it, answer, eos_hit)
        rec = {
            **{k: it[k] for k in ("round", "kind", "family", "prompt", "gold") if k in it},
            "accept": it.get("accept", []),
            "tol": it.get("tol", 0.0),
            "answer": answer,
            "answer_tokens": ntok,
            "eos_hit": eos_hit,
            "wall_s": wall,
            "correct": bool(res.is_correct),
            "truncated": bool(res.truncated),
            "extracted": res.extracted,
            "note": res.note,
        }
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rec, indent=2))
        tmp.replace(out)
        mark = "OK " if res.is_correct else ("TR " if res.truncated else "XX ")
        print(f"[{i:02d}] {mark}{it['kind']:16s} gold={it['gold']!r:20s} got={res.extracted!r:14s} "
              f"tok={ntok} eos={int(eos_hit)} t={wall:.1f}s", flush=True)

    # summarize per-kind and per-family (truncated items excluded from denominator, reported)
    summarize(items)
    print(f"[calib] wall {time.perf_counter()-t0:.1f}s", flush=True)


def summarize(items):
    by_kind = defaultdict(lambda: {"n": 0, "correct": 0, "truncated": 0})
    by_fam = defaultdict(lambda: {"n": 0, "correct": 0, "truncated": 0})
    per_item = []
    for it in items:
        out = RESULTS_DIR / f"{item_key(it)}.json"
        if not out.exists():
            continue
        rec = json.loads(out.read_text())
        k, f = rec["kind"], rec["family"]
        trunc = rec["truncated"]
        cor = rec["correct"]
        for agg in (by_kind[k], by_fam[f]):
            agg["truncated"] += int(trunc)
            if not trunc:
                agg["n"] += 1
                agg["correct"] += int(cor)
        per_item.append(rec)

    def acc(d):
        return d["correct"] / d["n"] if d["n"] else float("nan")

    lines = []
    lines.append("=== PER-KIND accuracy (truncated excluded from denominator) ===")
    for k in sorted(by_kind):
        d = by_kind[k]
        lines.append(f"  {k:16s} n={d['n']:2d} correct={d['correct']:2d} "
                     f"acc={acc(d):.3f} trunc={d['truncated']}  "
                     f"{'<-- BAND' if 0.30 <= acc(d) <= 0.80 else ''}")
    lines.append("=== PER-FAMILY accuracy ===")
    for f in sorted(by_fam):
        d = by_fam[f]
        lines.append(f"  {f:12s} n={d['n']:2d} correct={d['correct']:2d} acc={acc(d):.3f} "
                     f"trunc={d['truncated']}")
    summary_txt = "\n".join(lines)
    print(summary_txt, flush=True)
    (RESULTS_DIR / "summary.json").write_text(json.dumps({
        "by_kind": {k: {**v, "acc": acc(v)} for k, v in by_kind.items()},
        "by_family": {f: {**v, "acc": acc(v)} for f, v in by_fam.items()},
    }, indent=2))
    (RESULTS_DIR / "summary.txt").write_text(summary_txt)


if __name__ == "__main__":
    main()
