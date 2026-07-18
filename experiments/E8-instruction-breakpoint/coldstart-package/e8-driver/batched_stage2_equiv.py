"""E8 STAGE-2 batched-vs-per-call equivalence gate.

Proves the batched Stage-2 scorer (batched_stage2_scorer) produces the SAME per-item booleans as the
frozen per-call path (score_worker.score_one_task) on the SAME inputs on the SAME device. The two
differ ONLY in batch composition (fixed canonical cross-task batches vs frozen per-__call__ batches);
the float path is not bit-invariant to padding, so a delta is expected and a boolean FLIP is the
failure. PASS iff zero flips (and zero contamination/completeness-fraction disagreements, which are
derived from the same booleans). Exits nonzero + loud FAIL on any flip or task/item-set mismatch.

Per-call reference: score_worker.score_one_task(scalar, task, gen_by_arm, pruned_ids, arms) — the
registered per-task path, invoked verbatim, ONE shared scorer instance used by both paths so the only
exercised difference is batch grouping.

Compared units, per (task_id, arm):
  - must_change_asserted_by_index : {orig_index: bool}   (per-item change flags)
  - must_persist_asserted         : [bool]               (per-item persist flags)
  - contamination, completeness   : floats derived from those bools (checked for exact equality —
                                    they must match once the bools match; a mismatch is a bug here)

--n-tasks restricts to a cheap shard for a fast pre-gate.

Run on the Mini:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/batched_stage2_equiv.py \
      --tasks <corpus-candidates/<axis>.jsonl> --gen-log ~/e8-run/<axis>-stage2/stage2-gen.jsonl \
      --pruned ~/e8-run/<axis>-filter/pruned-items.json \
      --out ~/e8-run/<axis>-stage2/batched-stage2-equiv.json --device mps
  echo "exit=$?"   # nonzero => a boolean flipped => Stage-2 batched scorer NOT safe here
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
from common import atomic_write_json, load_pruned, set_cpu_threads  # noqa: E402
import batched_scorer          # noqa: E402  (build_scorer, score_pairs_batched)
import batched_stage2_scorer   # noqa: E402  (collect_pairs, reassemble, build_task_results, index_gens)
import score_worker            # noqa: E402  (score_one_task — the per-call reference)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _dist(xs):
    if not xs:
        return {}
    s = sorted(xs)
    n = len(s)
    return {"n": n, "max": max(s), "mean": sum(s) / n,
            "gt_1e-6": sum(1 for x in s if x > 1e-6),
            "gt_1e-4": sum(1 for x in s if x > 1e-4)}


def _per_item_bools_from_percall(rec: dict, arm: str):
    """Extract comparable per-item bools from a score_one_task result for one arm.
    Returns (change_by_index:dict[int,bool], persist_list:list[bool], contamination, completeness)."""
    a = rec["arms"][arm]
    change = {int(k): bool(v) for k, v in a["must_change_asserted_by_index"].items()}
    persist = [bool(b) for b in a["must_persist_asserted"]]
    return change, persist, a["contamination"], a["completeness"]


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 Stage-2 batched-vs-per-call equivalence gate")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--pruned", type=Path, default=Path("/dev/null"))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--arms", default="B")
    ap.add_argument("--n-tasks", type=int, default=None, help="restrict to first N tasks (cheap gate)")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--device", type=str, default="mps")
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--banked-config-hash", type=str, default=None)
    args = ap.parse_args()

    set_cpu_threads(args.threads)
    from closure_harness.config import CONFIG, config_hash as live_config_hash
    threshold = CONFIG.outcome.assert_threshold
    batch_size = args.batch_size if args.batch_size is not None else CONFIG.nli.batch_size
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())

    banked_hash = args.banked_config_hash
    if banked_hash is None:
        with args.gen_log.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    banked_hash = json.loads(line).get("config_hash")
                    break
    if not banked_hash:
        raise SystemExit("could not determine banked config_hash; pass --banked-config-hash")

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    if args.n_tasks:
        tasks = tasks[:args.n_tasks]
    pruned = load_pruned(args.pruned)
    gens = batched_stage2_scorer.index_gens(args.gen_log, banked_hash)
    _log(f"[s2-equiv] {len(tasks)} tasks, arms={arms}, device={args.device}, "
         f"banked_hash={banked_hash[:12]}, batch_size={batch_size}")

    t0 = time.time()
    scorer, det = batched_scorer.build_scorer(args.device)  # ONE scorer, BOTH paths
    _log(f"[s2-equiv] scorer built on {args.device}; warn_only needed: {det['warn_only_used']}")

    # ---- per-call reference: score_worker.score_one_task per task (frozen per-__call__ batching) ----
    _log("[s2-equiv] scoring per-call (score_worker.score_one_task) ...")
    percall = {}   # (task_id, arm) -> (change_by_index, persist_list, contam, complete)
    percall_tasks = 0
    for task in tasks:
        tid = task["task_id"]
        gen_by_arm = {a: gens.get((tid, a)) for a in arms}
        if any(v is None for v in gen_by_arm.values()):
            continue  # gen not ready — same skip as score_worker.py:187-190 and the batched path
        rec = score_worker.score_one_task(scorer, task, gen_by_arm, pruned.get(tid, set()), arms)
        for arm in arms:
            percall[(tid, arm)] = _per_item_bools_from_percall(rec, arm)
        percall_tasks += 1

    # ---- batched path (fixed canonical composition) ----
    _log("[s2-equiv] scoring batched (fixed canonical composition) ...")
    pairs, pair_meta, items, per_task = batched_stage2_scorer.collect_pairs(tasks, gens, pruned, arms)
    pair_scores = batched_scorer.score_pairs_batched(scorer, pairs, batch_size, use_fp16=False)
    item_scalars = batched_stage2_scorer.reassemble_item_scalars(pair_meta, pair_scores, items, threshold)
    batched_results = batched_stage2_scorer.build_task_results(per_task, item_scalars, arms, {})

    # ---- diff per (task, arm): every change flag + every persist flag ----
    flips = []          # list of {key, side, index, per_call, batched}
    frac_mismatches = []
    deltas = []         # not directly available (booleans compared); track fraction deltas
    compared_units = 0
    key_mismatch = []

    batched_percall_keys = set()
    for tid, rec in batched_results.items():
        for arm in rec["arms"]:
            batched_percall_keys.add((tid, arm))
    pc_keys = set(percall.keys())
    only_percall = sorted(pc_keys - batched_percall_keys)
    only_batched = sorted(batched_percall_keys - pc_keys)
    if only_percall or only_batched:
        key_mismatch = {"only_percall": [list(k) for k in only_percall[:20]],
                        "only_batched": [list(k) for k in only_batched[:20]],
                        "n_only_percall": len(only_percall), "n_only_batched": len(only_batched)}

    for (tid, arm) in sorted(pc_keys & batched_percall_keys):
        pc_change, pc_persist, pc_contam, pc_complete = percall[(tid, arm)]
        b = batched_results[tid]["arms"][arm]
        b_change = {int(k): bool(v) for k, v in b["must_change_asserted_by_index"].items()}
        b_persist = [bool(x) for x in b["must_persist_asserted"]]

        # change flags (keyed by original index)
        for idx in sorted(set(pc_change) | set(b_change)):
            compared_units += 1
            pv, bv = pc_change.get(idx), b_change.get(idx)
            if pv != bv:
                flips.append({"key": [tid, arm], "side": "must_change", "index": idx,
                              "per_call": pv, "batched": bv})
        # persist flags (positional list)
        for i in range(max(len(pc_persist), len(b_persist))):
            compared_units += 1
            pv = pc_persist[i] if i < len(pc_persist) else None
            bv = b_persist[i] if i < len(b_persist) else None
            if pv != bv:
                flips.append({"key": [tid, arm], "side": "must_persist", "index": i,
                              "per_call": pv, "batched": bv})
        # fraction agreement (must match once bools match; a mismatch here is a derivation bug)
        if abs(pc_contam - b["contamination"]) > 1e-12:
            frac_mismatches.append({"key": [tid, arm], "field": "contamination",
                                    "per_call": pc_contam, "batched": b["contamination"]})
        if abs(pc_complete - b["completeness"]) > 1e-12:
            frac_mismatches.append({"key": [tid, arm], "field": "completeness",
                                    "per_call": pc_complete, "batched": b["completeness"]})

    passed = (len(flips) == 0) and (len(frac_mismatches) == 0) and not key_mismatch

    report = {
        "tool": "batched_stage2_equiv",
        "verdict": "PASS" if passed else "FAIL",
        "banked_config_hash": banked_hash,
        "live_config_hash": live_config_hash(),
        "device": args.device,
        "warn_only_needed": det["warn_only_used"],
        "batch_size": batch_size,
        "assert_threshold": threshold,
        "n_tasks": len(tasks),
        "n_tasks_compared": percall_tasks,
        "n_units_compared": compared_units,
        "boolean_flips": len(flips),
        "flip_rate": (len(flips) / compared_units) if compared_units else 0.0,
        "fraction_mismatches": len(frac_mismatches),
        "key_set_mismatch": key_mismatch,
        "flip_examples": flips[:20],
        "fraction_mismatch_examples": frac_mismatches[:20],
        "pair_count": len(pairs),
        "elapsed_s": round(time.time() - t0, 1),
        "note": ("Same device both paths; only batch composition differs. Zero flips => Stage-2 "
                 "re-batching moves no decision across the 0.7 line for this corpus/model/device."),
    }
    atomic_write_json(args.out, report)
    _log("[s2-equiv] RESULT " + json.dumps({
        "verdict": report["verdict"], "flips": len(flips),
        "frac_mismatches": len(frac_mismatches), "units": compared_units,
        "tasks_compared": percall_tasks, "key_mismatch": bool(key_mismatch),
    }))
    _log(f"[s2-equiv] wrote {args.out}")

    if not passed:
        _log("[s2-equiv] *** FAIL: Stage-2 batched scoring diverged (flip / fraction / key mismatch). "
             "Do NOT use the batched Stage-2 output. Investigate before proceeding.")
        sys.exit(1)
    _log("[s2-equiv] PASS: zero flips — batched Stage-2 scorer equivalent to the per-call path here.")


if __name__ == "__main__":
    main()
