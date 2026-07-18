"""E8 BATCHED MPS scorer — minutes-scale filter-tier scoring, numerics mirrored from the frozen path.

Purpose: score a filter-gen log (the banked A1/A2/A3 filter draws) on Apple MPS by collecting ALL
(premise, hypothesis) pairs across families/states/draws/items/sources into fixed-composition,
canonically-ordered batches, so a full axis scores in minutes instead of the per-call ~11 s/family.

WHAT THIS IS NOT: it is NOT claimed bit-identical to the banked CPU scores. The frozen scoring path
(closure_harness/nli.py) batches pairs PER __call__ (one premise-list × one conclusion) in bs=16 in
pair-append order; the config comment (config.py:27-31) states a pair's score depends on its batch
composition because the float path is not bit-invariant to padding. This scorer deliberately RE-BATCHES
across items (that is the whole speedup), so its batch composition differs from the frozen per-call
composition. The batch composition here is therefore FIXED and DOCUMENTED (canonical sort + fixed chunk
size), and equivalence to the per-call path is proven EMPIRICALLY by batched_equiv.py (boolean-flip
gate), never assumed. Padding-induced last-ULP deltas are expected; a boolean flip near the 0.7
threshold is the only thing that matters, and batched_equiv.py is what measures it.

NUMERICS — every choice traces to the frozen source (cited here and in BATCHED-NOTES.md):
  - scalar per directional pair: (P(entail) - P(contradict) + 1)/2         nli.py:113
  - softmax over logits, dim=-1                                            nli.py:110
  - entail/contradict indices from model.config.label2id (lowercased)      nli.py:73-75
  - tokenizer(premises, hypotheses, truncation=True, max_length=512,
    padding=True, return_tensors="pt")                                     nli.py:88-95
  - fail-closed on truncation (raise if any pair > max_length)             nli.py:99-106
  - bidirectional: average (src,claim) and (claim,src)                     nli.py:123-126
  - multi-source: max over per-source bidirectional averages               nli.py:127
  - empty sources -> 0.0                                                   nli.py:119
  - checkpoint/revision/max_length/batch_size/device from frozen NLIConfig config.py:16-36
  - item = must_change conclusion; premises = _asserted_text(output)       filter_stage.py:136 /
                                                                           outcomes.py:40-49
  - gen indexing (task_id, filter_state, draw) selection + config_hash gate filter_stage.py:120-123
  - threshold = CONFIG.outcome.assert_threshold (0.7)                      config.py:57 / outcomes.py:54

DEVICE / DETERMINISM: MPS is engaged exactly as gpu_probe.py does — dataclasses.replace(CONFIG.nli,
device="mps") plus a monkeypatch of torch.use_deterministic_algorithms so the frozen __init__'s
unconditional True cannot hard-fail on MPS, recording whether warn_only was needed. Frozen files and
existing e8-driver files are byte-untouched; this module only imports them.

DTYPE: whatever the frozen config loads (fp32 model weights, no autocast). --fp16 exists but defaults
OFF and prints a loud numerics warning; fp16 changes the reduction and is not the frozen path.

CLI shape mirrors gpu_probe.py: --tasks --gen-log --out --n-draws --threads --device (default mps).
Run on the Mini:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/batched_scorer.py \
      --tasks <tasks.jsonl> --gen-log ~/e8-run/A3-filter/filter-gen.jsonl \
      --out ~/e8-run/A3-filter/batched-scores.json --n-draws 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
import filter_stage  # noqa: E402  (top_level_per_family — same family selection as the frozen path)
from common import atomic_write_json, load_jsonl, set_cpu_threads  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# --------------------------------------------------------------------------- frozen scorer on device
def build_scorer(device: str):
    """Construct the FROZEN NLIScorer on `device`. Returns (scorer, det_state).

    device == "cpu" builds it verbatim (frozen default). Any other device (mps/cuda) monkeypatches
    torch.use_deterministic_algorithms the SAME measured way gpu_probe.build_mps_scorer does, so the
    frozen __init__'s unconditional True call cannot hard-fail where deterministic kernels are absent,
    and records whether warn_only was actually exercised. The monkeypatch is restored in a finally so
    the frozen module state is left exactly as found (hermetic)."""
    import torch
    from closure_harness.config import CONFIG

    state = {"warn_only_used": False, "strict_raised": False}

    if device == "cpu":
        from closure_harness.nli import NLIScorer
        return NLIScorer(config=CONFIG.nli), state

    orig = torch.use_deterministic_algorithms

    def patched(mode, *a, **kw):
        try:
            return orig(mode, *a, **kw)
        except Exception as e:  # noqa: BLE001 — probing exactly this failure, as gpu_probe does
            state["strict_raised"] = True
            state["warn_only_used"] = True
            _log(f"[batched] use_deterministic_algorithms strict rejected on {device} "
                 f"({type(e).__name__}: {e}); retrying warn_only=True")
            return orig(mode, warn_only=True)

    torch.use_deterministic_algorithms = patched
    try:
        from closure_harness.nli import NLIScorer
        cfg = replace(CONFIG.nli, device=device)
        scorer = NLIScorer(config=cfg)
    finally:
        torch.use_deterministic_algorithms = orig  # restore — keep the frozen module untouched
    return scorer, state


# --------------------------------------------------------------------------- gen indexing (frozen shape)
def index_gens(gen_log: Path, config_hash: str) -> dict:
    """(task_id, filter_state, draw_index) -> output — identical selection to
    filter_stage.score_draws (filter_stage.py:120-123) and gpu_probe.index_gens."""
    gens: dict[tuple, dict] = {}
    for r in load_jsonl(gen_log):
        if r.get("config_hash") == config_hash and not r.get("error") and "filter_state" in r:
            gens[(r["task_id"], r["filter_state"], r["draw_index"])] = r["output"]
    return gens


# --------------------------------------------------------------------------- pair collection
# Canonical ordering of the FULL pair list. The sort key is a total order over every directional
# pair in the corpus; chunking this sorted list into fixed-size batches FIXES the batch composition,
# which is what determines the fp reduction order (and hence exact reproducibility of THIS scorer's
# own numbers). Documented so a replayer reproduces batched-scores.json bit-for-bit on the same
# device/build. It is NOT the frozen per-call composition — see module docstring.
#
# key = (family_id, state_rank, draw, item_idx, source_idx, direction)
#   state_rank: assumption=0, correction=1 (stable, state-name-independent)
#   direction:  0 = (source, claim)   [premise=source, hypothesis=claim]  nli.py:123
#               1 = (claim, source)   [swapped]                            nli.py:124
_STATE_RANK = {"assumption": 0, "correction": 1}


def collect_pairs(top: dict, gens: dict, n_draws: int):
    """Walk the SAME nested structure as gpu_probe.score_all / filter_stage.score_draws and emit one
    record per directional pair. Returns:
      pairs:      list[(premise:str, hypothesis:str)]   in canonical order
      pair_meta:  list[(fam, state, draw, item_idx, source_idx, direction)]  aligned to `pairs`
      items:      dict[(fam,state,draw,item_idx)] -> n_sources   (0 => scalar is 0.0, no pairs)
    Missing gens (holes) are skipped exactly as the frozen path skips (g is None -> continue),
    filter_stage.py:133-135. An item with zero asserted premises (empty sources) produces NO pairs
    and is recorded with n_sources=0 so reassembly returns 0.0 (nli.py:119)."""
    from closure_harness.schema import parse_output
    from closure_harness.outcomes import _asserted_text

    records = []  # (sort_key, premise, hypothesis, item_key, source_idx, direction)
    items: dict[tuple, int] = {}
    fams = sorted(top.keys())
    for fam in fams:
        task = top[fam]
        mc = task["must_change"]
        for state in ("assumption", "correction"):
            for d in range(n_draws):
                g = gens.get((task["task_id"], state, d))
                if g is None:
                    continue  # hole — identical to frozen skip (filter_stage.py:133-135)
                o = parse_output(g)                 # frozen schema validation (schema.py:27)
                premises = _asserted_text(o)        # frozen premise set (outcomes.py:40-49)
                for i, concl in enumerate(mc):
                    item_key = (fam, state, d, i)
                    items[item_key] = len(premises)
                    for s_idx, src in enumerate(premises):
                        # two directions per source, mirroring nli.__call__ lines 123-124
                        for direction, (prem, hyp) in enumerate(((src, concl), (concl, src))):
                            sort_key = (fam, _STATE_RANK[state], d, i, s_idx, direction)
                            records.append((sort_key, prem, hyp, item_key, s_idx, direction))

    records.sort(key=lambda r: r[0])  # canonical total order — fixes batch composition
    pairs = [(r[1], r[2]) for r in records]
    pair_meta = [(r[3], r[4], r[5]) for r in records]  # (item_key, source_idx, direction)
    return pairs, pair_meta, items


# --------------------------------------------------------------------------- batched forward
def score_pairs_batched(scorer, pairs, batch_size: int, use_fp16: bool):
    """Vectorized replica of nli._pair_scores over the FULL canonical pair list.

    Identical intent to nli.py:77-115, only the batch grouping differs (fixed canonical chunks
    instead of per-__call__ chunks). Same tokenizer call, same truncation fail-closed, same softmax,
    same entail/contradict indices, same (entail-contradict+1)/2 scalar. Returns list[float] aligned
    to `pairs`."""
    if not pairs:
        return []
    torch = scorer._torch
    tok = scorer.tokenizer
    model = scorer.model
    max_length = scorer.config.max_length
    entail_idx = scorer._entail_idx
    contradict_idx = scorer._contradict_idx
    device = scorer.device

    out: list[float] = []
    n = len(pairs)
    n_batches = (n + batch_size - 1) // batch_size
    for bi, start in enumerate(range(0, n, batch_size), 1):
        chunk = pairs[start:start + batch_size]
        premises = [p for p, _ in chunk]
        hypotheses = [h for _, h in chunk]
        enc = tok(
            premises,
            hypotheses,
            truncation=True,
            max_length=max_length,
            padding=True,
            return_tensors="pt",
        )
        # Fail closed on truncation — verbatim intent of nli.py:99-106. If the padded batch reached
        # max_length, re-measure each pair's true length and raise if any genuinely exceeds it
        # (a truncated premise silently changes what "grounded" means).
        if enc["input_ids"].shape[1] >= max_length:
            lengths = [len(tok(p, h)["input_ids"]) for p, h in chunk]
            over = [i for i, ln in enumerate(lengths) if ln > max_length]
            if over:
                raise ValueError(
                    f"NLI input exceeds max_length={max_length} for pair indices {over} in "
                    f"batch {bi} (global offset {start}); exclude or shorten the source text "
                    "(mirrors closure_harness/nli.py:99-106)"
                )
        enc = enc.to(device)
        with torch.no_grad():
            if use_fp16:
                with torch.autocast(device_type=device.type, dtype=torch.float16):
                    logits = model(**enc).logits
            else:
                logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1)
        entail = probs[:, entail_idx]
        contradict = probs[:, contradict_idx]
        scalars = (entail - contradict + 1.0) / 2.0
        out.extend(float(x) for x in scalars.detach().cpu().tolist())
        if bi % 50 == 0 or bi == n_batches:
            _log(f"[batched] forward {bi}/{n_batches} batches ({start + len(chunk)}/{n} pairs)")
    return out


# --------------------------------------------------------------------------- reassembly
def reassemble(pair_meta, pair_scores, items, threshold: float):
    """Fold directional pair scores back into per-item scalars, mirroring nli.__call__:
      per source: bidirectional average of its two directions   (nli.py:126)
      per item:   max over sources                               (nli.py:127)
      empty sources: 0.0                                         (nli.py:119)
    Returns {(fam,state,draw,item_idx): (raw_float, bool >= threshold)}."""
    # group directional scores by (item_key, source_idx) -> {direction: score}
    by_src: dict[tuple, dict] = {}
    for (item_key, s_idx, direction), sc in zip(pair_meta, pair_scores):
        by_src.setdefault((item_key, s_idx), {})[direction] = sc

    # per-item max over sources of bidirectional averages
    per_item_best: dict[tuple, float] = {}
    for (item_key, s_idx), dirs in by_src.items():
        if 0 not in dirs or 1 not in dirs:
            # both directions are always emitted together in collect_pairs; a missing one is a bug
            raise ValueError(
                f"incomplete direction set for {item_key} source {s_idx}: have {sorted(dirs)}"
            )
        bidir = (dirs[0] + dirs[1]) / 2.0  # nli.py:126
        prev = per_item_best.get(item_key)
        if prev is None or bidir > prev:
            per_item_best[item_key] = bidir

    result: dict[tuple, tuple] = {}
    for item_key, n_sources in items.items():
        if n_sources == 0:
            raw = 0.0  # empty sources -> 0.0 (nli.py:119); never crosses threshold
        else:
            raw = per_item_best[item_key]  # KeyError here would mean a pair went missing — loud
        result[item_key] = (raw, raw >= threshold)
    return result


# --------------------------------------------------------------------------- output shape
def _score_all_shape(result: dict) -> dict:
    """Serialize {(fam,state,draw,item): (raw,bool)} to JSON. Keys are '||'-joined so the structure
    survives JSON (tuples are not JSON keys) and round-trips uniquely (family ids / states contain no
    '||'). Same (fam,state,draw,item) identity as gpu_probe.score_all's dict keys."""
    scores = {}
    for (fam, state, draw, item), (raw, b) in result.items():
        scores[f"{fam}||{state}||{draw}||{item}"] = {"raw": raw, "assert": bool(b)}
    return scores


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 batched MPS scorer (fixed-composition, equiv-gated)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--threads", type=int, default=2, help="CPU threads for tokenization")
    ap.add_argument("--device", type=str, default="mps",
                    help="torch device for the frozen scorer (default mps; cpu for A/B baselines)")
    ap.add_argument("--batch-size", type=int, default=None,
                    help="pairs per forward batch; default = frozen NLIConfig.batch_size (16). "
                         "Changing this CHANGES the fixed batch composition and hence exact numbers.")
    ap.add_argument("--families", type=str, default=None,
                    help="comma-separated family ids to restrict to (cheap shard)")
    ap.add_argument("--fp16", action="store_true",
                    help="use float16 autocast on the forward pass — NOT the frozen numerics")
    args = ap.parse_args()

    set_cpu_threads(args.threads)  # tokenization is CPU; also sets offline env (common.py:175-183)
    from closure_harness.config import CONFIG, config_hash
    CH = config_hash()
    threshold = CONFIG.outcome.assert_threshold
    batch_size = args.batch_size if args.batch_size is not None else CONFIG.nli.batch_size

    if args.fp16:
        _log("[batched] *** WARNING: --fp16 enabled. This is NOT the frozen numeric path. "
             "fp16 autocast changes softmax/reduction precision; batched_equiv WILL likely show "
             "deltas and possibly flips. Use only for throughput experiments, never for a scored run.")

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)  # frozen family selection (filter_stage.py:41)
    if args.families:
        keep = set(args.families.split(","))
        top = {f: t for f, t in top.items() if f in keep}
    gens = index_gens(args.gen_log, CH)
    _log(f"[batched] {len(top)} families, threshold={threshold}, batch_size={batch_size}, "
         f"device={args.device}, config_hash={CH[:12]}")

    t0 = time.time()
    scorer, det_state = build_scorer(args.device)
    _log(f"[batched] scorer built on {args.device}; warn_only needed: {det_state['warn_only_used']}")

    pairs, pair_meta, items = collect_pairs(top, gens, args.n_draws)
    _log(f"[batched] collected {len(pairs)} directional pairs across {len(items)} items")

    t_fwd = time.time()
    pair_scores = score_pairs_batched(scorer, pairs, batch_size, args.fp16)
    fwd_elapsed = time.time() - t_fwd

    result = reassemble(pair_meta, pair_scores, items, threshold)
    scores = _score_all_shape(result)
    n_assert = sum(1 for v in scores.values() if v["assert"])
    elapsed = time.time() - t0

    report = {
        "tool": "batched_scorer",
        "scores": scores,
        "meta": {
            "config_hash": CH,
            "assert_threshold": threshold,
            "device": args.device,
            "warn_only_needed": det_state["warn_only_used"],
            "strict_raised": det_state["strict_raised"],
            "batch_size": batch_size,
            "fp16": bool(args.fp16),
            "n_families": len(top),
            "n_items": len(items),
            "n_assert": n_assert,
            "pair_count": len(pairs),
            "n_draws": args.n_draws,
            "families_filter": args.families,
            "canonical_ordering": (
                "pairs sorted by (family_id, state_rank[assumption=0,correction=1], draw, "
                "item_idx, source_idx, direction[0=(source,claim),1=(claim,source)]); chunked into "
                "fixed batch_size batches. Fixed composition => fixed fp reduction order => "
                "reproducible on same device/build. NOT the frozen per-call composition — equivalence "
                "is proven by batched_equiv.py, not assumed."
            ),
            "numerics_source": "closure_harness/nli.py (scalar 113, softmax 110, indices 73-75, "
                               "truncation 99-106, bidir 126, max-over-sources 127, empty->0 119)",
            "elapsed_s": round(elapsed, 1),
            "forward_elapsed_s": round(fwd_elapsed, 1),
            "pairs_per_s": round(len(pairs) / fwd_elapsed, 2) if fwd_elapsed > 0 else None,
        },
    }
    atomic_write_json(args.out, report)
    _log("[batched] RESULT " + json.dumps({
        "n_items": len(items), "n_assert": n_assert, "pair_count": len(pairs),
        "device": args.device, "elapsed_s": report["meta"]["elapsed_s"],
        "pairs_per_s": report["meta"]["pairs_per_s"], "warn_only": det_state["warn_only_used"],
    }))
    _log(f"[batched] wrote {args.out}")


if __name__ == "__main__":
    main()
