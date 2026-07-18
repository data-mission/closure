"""E8 BATCHED-vs-PER-CALL equivalence gate — the certification that the batched scorer is safe.

The batched scorer (batched_scorer.py) re-batches pairs ACROSS items to go fast; the frozen path
(and gpu_probe.score_all, which mirrors it) batches PER __call__. Both are numerically identical in
INTENT (same checkpoint, indices, scalar, bidir/max aggregation) but differ in batch composition, and
the float path is not bit-invariant to padding (config.py:27-31). This tool MEASURES the consequence:

  Run BOTH on the SAME inputs on the SAME device, per (family,state,draw,item):
    - per_call:  gpu_probe.score_all(scorer, ...)      → frozen per-__call__ batching
    - batched:   batched_scorer.collect_pairs/score_pairs_batched/reassemble  → fixed canonical batches
  Diff:
    - BOOLEAN FLIPS (raw >= threshold): MUST be 0 to PASS. Any flip => exit nonzero, loud FAIL.
    - max |Δ| distribution on the raw scalars (expected tiny, padding-induced last-ULP noise).
    - near-threshold band (|per_call - 0.7| <= 0.05): where a delta is most likely to flip a bool.

Same-device comparison isolates batch composition as the ONLY variable (device float behavior is held
constant), which is exactly the thing batched_scorer introduces. A zero-flip result here means: for
THIS corpus/model/device, re-batching does not move any decision across the 0.7 line — the batched
scorer may be used for the scored run. A flip is a hard stop.

--families restricts to a cheap shard (e.g. the 4 smoke families) for a fast gate before the full pass.

Run on the Mini:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/batched_equiv.py \
      --tasks <tasks.jsonl> --gen-log ~/e8-run/A3-filter/filter-gen.jsonl \
      --out ~/e8-run/A3-filter/batched-equiv.json --n-draws 3 --device mps
  echo "exit=$?"   # nonzero => FAIL (a boolean flipped)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
import filter_stage  # noqa: E402
import gpu_probe      # noqa: E402  (score_all — the frozen per-__call__ path)
import batched_scorer  # noqa: E402  (collect_pairs / score_pairs_batched / reassemble / build_scorer)
from common import atomic_write_json  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _dist(xs):
    if not xs:
        return {}
    s = sorted(xs)
    n = len(s)
    return {
        "n": n, "max": max(s), "mean": sum(s) / n,
        "p50": s[n // 2], "p95": s[min(n - 1, int(n * 0.95))],
        "gt_1e-6": sum(1 for x in s if x > 1e-6),
        "gt_1e-4": sum(1 for x in s if x > 1e-4),
        "gt_1e-2": sum(1 for x in s if x > 1e-2),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 batched-vs-per-call equivalence gate")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--device", type=str, default="mps",
                    help="device for BOTH scorers — held constant so batch composition is the only "
                         "variable (default mps)")
    ap.add_argument("--batch-size", type=int, default=None,
                    help="batched scorer chunk size; default = frozen NLIConfig.batch_size")
    ap.add_argument("--families", type=str, default=None,
                    help="comma-separated family ids to restrict to (cheap shard gate)")
    args = ap.parse_args()

    from common import set_cpu_threads
    set_cpu_threads(args.threads)
    from closure_harness.config import CONFIG, config_hash
    CH = config_hash()
    threshold = CONFIG.outcome.assert_threshold
    batch_size = args.batch_size if args.batch_size is not None else CONFIG.nli.batch_size

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)
    if args.families:
        keep = set(args.families.split(","))
        top = {f: t for f, t in top.items() if f in keep}
    gens = batched_scorer.index_gens(args.gen_log, CH)
    _log(f"[equiv] {len(top)} families, threshold={threshold}, batch_size={batch_size}, "
         f"device={args.device}, config_hash={CH[:12]}")

    t0 = time.time()
    # ONE scorer instance, used by BOTH paths — same weights, same device, same indices. The only
    # difference exercised is how pairs are grouped into forward batches.
    scorer, det_state = batched_scorer.build_scorer(args.device)
    _log(f"[equiv] scorer built on {args.device}; warn_only needed: {det_state['warn_only_used']}")

    # ---- per-call (frozen per-__call__ batching) via the gpu_probe path ----
    _log("[equiv] scoring per-call (frozen per-__call__ path) ...")
    per_call = gpu_probe.score_all(scorer, top, gens, threshold, args.n_draws, "equiv-percall")
    # per_call: {(fam, state, draw, item_idx): (raw, bool)}

    # ---- batched (fixed canonical composition) ----
    _log("[equiv] scoring batched (fixed canonical composition) ...")
    pairs, pair_meta, items = batched_scorer.collect_pairs(top, gens, args.n_draws)
    pair_scores = batched_scorer.score_pairs_batched(scorer, pairs, batch_size, use_fp16=False)
    batched = batched_scorer.reassemble(pair_meta, pair_scores, items, threshold)
    # batched: {(fam, state, draw, item_idx): (raw, bool)}

    # ---- diff on the intersection (both must see identical item sets; a mismatch is itself a bug) ----
    keys = sorted(set(per_call.keys()) & set(batched.keys()))
    only_per_call = sorted(set(per_call.keys()) - set(batched.keys()))
    only_batched = sorted(set(batched.keys()) - set(per_call.keys()))

    flips = [k for k in keys if per_call[k][1] != batched[k][1]]
    deltas = [abs(per_call[k][0] - batched[k][0]) for k in keys]
    near = [k for k in keys if abs(per_call[k][0] - threshold) <= 0.05]
    near_flips = [k for k in near if per_call[k][1] != batched[k][1]]

    # a key-set mismatch means one path saw an item the other didn't — treat as a hard failure too
    key_mismatch = bool(only_per_call or only_batched)
    passed = (len(flips) == 0) and not key_mismatch

    report = {
        "tool": "batched_equiv",
        "verdict": "PASS" if passed else "FAIL",
        "config_hash": CH,
        "assert_threshold": threshold,
        "device": args.device,
        "batch_size": batch_size,
        "n_families": len(top),
        "n_items_compared": len(keys),
        "warn_only_needed": det_state["warn_only_used"],
        "strict_raised": det_state["strict_raised"],
        "boolean_flips": len(flips),
        "flip_rate": (len(flips) / len(keys)) if keys else 0.0,
        "key_set_mismatch": {
            "only_per_call": [list(k) for k in only_per_call[:20]],
            "only_batched": [list(k) for k in only_batched[:20]],
            "n_only_per_call": len(only_per_call),
            "n_only_batched": len(only_batched),
        },
        "score_delta_distribution": _dist(deltas),
        "near_threshold_pm0.05": {"n": len(near), "flips": len(near_flips)},
        "flip_examples": [
            {"key": list(k),
             "per_call": {"raw": per_call[k][0], "bool": per_call[k][1]},
             "batched": {"raw": batched[k][0], "bool": batched[k][1]}}
            for k in flips[:20]
        ],
        "pair_count": len(pairs),
        "elapsed_s": round(time.time() - t0, 1),
        "note": ("Same device for both paths; the ONLY variable is batch composition "
                 "(fixed canonical vs frozen per-__call__). Zero flips => re-batching moves no "
                 "decision across the 0.7 line for this corpus/model/device."),
    }
    atomic_write_json(args.out, report)
    _log("[equiv] RESULT " + json.dumps({
        "verdict": report["verdict"], "flips": len(flips),
        "flip_rate": round(report["flip_rate"], 6),
        "max_delta": report["score_delta_distribution"].get("max"),
        "near_flips": len(near_flips), "key_mismatch": key_mismatch,
        "n_items": len(keys),
    }))
    _log(f"[equiv] wrote {args.out}")

    if not passed:
        _log("[equiv] *** FAIL: batched scoring flipped a boolean (or item-set mismatch). "
             "The batched scorer is NOT safe for the scored run on this device/corpus. "
             "Do NOT use its output. Investigate before proceeding.")
        sys.exit(1)
    _log("[equiv] PASS: zero boolean flips — batched scorer is equivalent to the per-call path here.")


if __name__ == "__main__":
    main()
