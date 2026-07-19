"""E8 STAGE-2 BATCHED MPS scorer — registered-run scoring of the full corpus on GPU.

Mirrors score_worker.score_one_task (score_worker.py:53-138) the way batched_scorer mirrors
nli._pair_scores: identical numerics in intent, only the batch composition differs (fixed canonical
cross-task batches instead of the frozen per-__call__ batches). Produces the EXACT per-task result
shape the verdict compute-plan reads:
  {task_id, kept_change_indices, routing{family_id, axis, dose_level, break_side, verdict_item,
   verdict_item_defaulted, item_roles}, arms{<arm>{n_items, contaminated_items, contamination,
   completeness, must_change_asserted_by_index, must_persist_asserted}}, provenance, ts}

WHAT THIS IS NOT: bit-identical to the CPU-banked scores. The frozen path batches per outcomes.score
→ NLIScorer.__call__ (one premise-list × one conclusion) at bs=16; this scorer re-batches ACROSS
tasks/items (the speedup). Equivalence is proven EMPIRICALLY by batched_stage2_equiv.py (boolean-flip
gate), never assumed — same discipline as the filter tier's batched_equiv.

NUMERICS — every choice traces to the frozen source (cited in STAGE2-READINESS / here):
  - per conclusion: _still_asserts(scalar, output, concl, t) = scalar(_asserted_text(o), concl) >= t
      outcomes.py:52-54; _asserted_text = [conclusion, *claim texts]  outcomes.py:40-49
  - scalar = NLIScorer.__call__: per-source bidirectional avg, max over sources, empty→0
      nli.py:117-127; per-pair (entail-contradict+1)/2, softmax, indices  nli.py:113/110/73-75
  - contamination = fraction of must_change (post-prune) asserted; completeness = fraction of
      must_persist asserted  outcomes.py:80-86 (frozen score())
  - must_change = task.must_change MINUS pruned indices (keep list); must_persist = all
      score_worker.build_annotations (score_worker.py:38-50)
  - n_items = len(kept must_change); contaminated_items = round(contamination * n_items)
      score_worker.py:88-89
  - must_change_asserted_by_index keyed by ORIGINAL index keep[j]; must_persist_asserted a list
      score_worker.py:80-86
  - routing block (verdict_item all-true default when absent, break_side, dose_level int, item_roles)
      score_worker.py:96-132
  - gen selection: latest clean (task_id, arm) row at the banked config_hash, no error
      score_worker.py:172-175
  - pruning register load (task_id -> {item_index})  common.load_pruned

OPTIMIZATION NOTE (provably safe): score_one_task scores each conclusion TWICE — once inside frozen
score() (for the contamination/completeness fractions) and once for the per-item asserted flag. Both
are the SAME pure call scalar(premises, concl) with identical inputs, so this scorer scores each
unique (task, arm, side, item) conclusion ONCE and derives BOTH the fraction and the flag from it.
This changes nothing numerically (a pure function returns the same value); it only avoids double work.

DEVICE / HASH: MPS via the gpu_probe monkeypatch (records warn_only). Stage-2 gens are stamped with
the frozen CPU hash 6dbe47a8 (generation never touches the scorer device — lead-confirmed, same as
the filter tier). So record selection keys on the gen log's BANKED hash (auto-detected from the first
row), while --device moves ONLY the scorer — the reanchor_e5_mps.py pattern.

CLI mirrors batched_scorer + score_worker: --tasks --gen-log --pruned --out --arms --threads
--device (default mps) [--banked-config-hash] [--batch-size] [--families... no, tasks here] [--fp16].
Run on the Mini:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/batched_stage2_scorer.py \
      --tasks <corpus-candidates/<axis>.jsonl> --gen-log ~/e8-run/<axis>-stage2/stage2-gen.jsonl \
      --pruned ~/e8-run/<axis>-filter/pruned-items.json \
      --out ~/e8-run/<axis>-stage2/batched-stage2-scores.json --device mps
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
from common import atomic_write_json, load_jsonl, load_pruned, set_cpu_threads, capture_provenance  # noqa: E402
import batched_scorer  # noqa: E402  (reuse build_scorer, score_pairs_batched)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# --------------------------------------------------------------------------- gen indexing (frozen)
def index_gens(gen_log: Path, banked_hash: str) -> dict:
    """(task_id, arm) -> output — identical selection to score_worker.py:172-175, but keyed on the
    BANKED (CPU) hash rather than the live (MPS) hash so MPS scoring selects the CPU-stamped gens."""
    gens: dict[tuple, dict] = {}
    for r in load_jsonl(gen_log):
        if r.get("config_hash") == banked_hash and not r.get("error"):
            gens[(r["task_id"], r["arm"])] = r["output"]
    return gens


# --------------------------------------------------------------------------- pair collection
# Canonical ordering over EVERY directional pair across tasks/arms/sides/items/sources. Fixed
# composition => fixed fp reduction order => reproducible on same device/build. NOT the frozen
# per-__call__ composition (equivalence is the gate's job).
# key = (task_id, arm, side_rank, item_idx, source_idx, direction)
#   side_rank: must_change=0, must_persist=1  (stable, name-independent)
#   direction: 0 = (source, claim), 1 = (claim, source)   nli.py:123-124
_SIDE_RANK = {"change": 0, "persist": 1}


def build_annotations(task: dict, pruned_ids: set):
    """score_worker.build_annotations verbatim (score_worker.py:38-50): must_change MINUS pruned
    (keep list), must_persist = all. Returns (kept_change_texts, keep_indices, persist_texts)."""
    mc = task["must_change"]
    keep = [i for i in range(len(mc)) if i not in pruned_ids]
    kept_change = [mc[i] for i in keep]
    persist = list(task.get("must_persist", []))
    return kept_change, keep, persist


def collect_pairs(tasks, gens, pruned, arms):
    """Walk every (task, arm) with a clean gen, both annotation sides, and emit one record per
    directional pair. Returns pairs, pair_meta, items where:
      pairs:     list[(premise, hypothesis)] canonical order
      pair_meta: list[(item_key, source_idx, direction)]
      items:     dict[item_key] -> n_sources        item_key = (task_id, arm, side, item_idx)
    Missing gen (task/arm) is skipped (score_worker.py:187-190). Empty premises → n_sources=0 → 0.0.
    Also returns per_task carrying keep + routing inputs so reassembly can build the result shape."""
    from closure_harness.schema import parse_output
    from closure_harness.outcomes import _asserted_text

    records = []
    items: dict[tuple, int] = {}
    per_task = {}  # task_id -> {task, keep, kept_change, persist, arms_present}
    for task in tasks:
        tid = task["task_id"]
        pruned_ids = pruned.get(tid, set())
        kept_change, keep, persist = build_annotations(task, pruned_ids)
        arms_present = []
        for arm in arms:
            g = gens.get((tid, arm))
            if g is None:
                continue  # gen not ready — skip exactly like score_worker.py:187-190
            arms_present.append(arm)
            o = parse_output(g)                      # frozen schema validation
            premises = _asserted_text(o)             # frozen premise set (outcomes.py:40-49)
            for side, concls in (("change", kept_change), ("persist", persist)):
                for item_idx, concl in enumerate(concls):
                    item_key = (tid, arm, side, item_idx)
                    items[item_key] = len(premises)
                    for s_idx, src in enumerate(premises):
                        for direction, (prem, hyp) in enumerate(((src, concl), (concl, src))):
                            sort_key = (tid, arm, _SIDE_RANK[side], item_idx, s_idx, direction)
                            records.append((sort_key, prem, hyp, item_key, s_idx, direction))
        per_task[tid] = {"task": task, "keep": keep, "kept_change": kept_change,
                         "persist": persist, "arms_present": arms_present}

    records.sort(key=lambda r: r[0])
    pairs = [(r[1], r[2]) for r in records]
    pair_meta = [(r[3], r[4], r[5]) for r in records]
    return pairs, pair_meta, items, per_task


# --------------------------------------------------------------------------- reassembly
def reassemble_item_scalars(pair_meta, pair_scores, items, threshold):
    """Fold directional pair scores into per-item (raw, bool) exactly like nli.__call__:
    per-source bidirectional average (nli.py:126), max over sources (nli.py:127), empty→0 (nli.py:119).
    Returns {item_key: (raw, bool)} with item_key = (task_id, arm, side, item_idx)."""
    by_src: dict[tuple, dict] = {}
    for (item_key, s_idx, direction), sc in zip(pair_meta, pair_scores):
        by_src.setdefault((item_key, s_idx), {})[direction] = sc

    per_item_best: dict[tuple, float] = {}
    for (item_key, s_idx), dirs in by_src.items():
        if 0 not in dirs or 1 not in dirs:
            raise ValueError(f"incomplete direction set for {item_key} source {s_idx}: {sorted(dirs)}")
        bidir = (dirs[0] + dirs[1]) / 2.0
        prev = per_item_best.get(item_key)
        if prev is None or bidir > prev:
            per_item_best[item_key] = bidir

    result = {}
    for item_key, n_sources in items.items():
        raw = 0.0 if n_sources == 0 else per_item_best[item_key]
        result[item_key] = (raw, raw >= threshold)
    return result


# --------------------------------------------------------------------------- result shape
def build_task_results(per_task, item_scalars, arms, prov_dict):
    """Assemble the score_worker per-task result records from the per-item scalars. Mirrors
    score_one_task (score_worker.py:73-138): contamination/completeness fractions, per-item flags
    keyed by original index, routing block. Returns {task_id: result_dict}."""
    out = {}
    for tid, info in per_task.items():
        task = info["task"]
        keep = info["keep"]
        kept_change = info["kept_change"]
        persist = info["persist"]
        n = len(kept_change)

        per_arm = {}
        for arm in info["arms_present"]:
            # per-item bools for this arm/side
            change_bools = [item_scalars[(tid, arm, "change", j)][1] for j in range(len(kept_change))]
            persist_bools = [item_scalars[(tid, arm, "persist", j)][1] for j in range(len(persist))]
            # contamination = fraction of kept must_change asserted (outcomes.py:80-82)
            contamination = (sum(change_bools) / n) if n else _empty_side_raises(tid, "must_change")
            # completeness = fraction of must_persist asserted (outcomes.py:83-85)
            np_ = len(persist)
            completeness = (sum(persist_bools) / np_) if np_ else _empty_side_raises(tid, "must_persist")
            change_asserted = {keep[j]: bool(change_bools[j]) for j in range(len(kept_change))}
            per_arm[arm] = {
                "n_items": n,
                "contaminated_items": round(contamination * n),
                "contamination": contamination,
                "completeness": completeness,
                "must_change_asserted_by_index": {str(k): v for k, v in change_asserted.items()},
                "must_persist_asserted": [bool(b) for b in persist_bools],
            }

        # routing block (score_worker.py:96-132)
        ap = task.get("axis_params", {}) if isinstance(task.get("axis_params"), dict) else {}
        break_side = task.get("break_side")
        break_items = task.get(break_side) if break_side in ("must_change", "must_persist") \
            else task.get("must_change", [])
        n_break = len(break_items) if isinstance(break_items, list) else 0
        raw_vi = ap.get("verdict_item")
        verdict_item = raw_vi if isinstance(raw_vi, list) else [True] * n_break
        verdict_item_defaulted = not isinstance(raw_vi, list)
        routing = {
            "family_id": task.get("family_id"),
            "axis": task.get("axis"),
            "dose_level": task.get("dose_level"),
            "break_side": break_side,
            "verdict_item": verdict_item,
            "verdict_item_defaulted": verdict_item_defaulted,
            "item_roles": ap.get("item_roles"),
        }
        out[tid] = {
            "task_id": tid,
            "kept_change_indices": keep,
            "routing": routing,
            "arms": per_arm,
            "provenance": prov_dict,
            "ts": _ts(),
        }
    return out


def _empty_side_raises(tid, which):
    # frozen outcomes.score() raises on an empty annotation side (outcomes.py:74-78). Mirror that:
    # a task with an empty must_change/must_persist is a construction error, fail loud.
    raise ValueError(f"task {tid}: empty {which} — frozen scoring raises (outcomes.py:74-78); "
                     "exclude the task upstream")


def _write_per_task_files(results: dict, out_dir: Path) -> int:
    """Also emit one atomic JSON per task under out_dir (score_worker's on-disk layout the verdict
    compute-plan reads: results/<task_id>.json). Returns count written."""
    n = 0
    for tid, rec in results.items():
        atomic_write_json(out_dir / f"{tid}.json", rec)
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 Stage-2 batched MPS scorer (score_worker shape)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--pruned", type=Path, default=Path("/dev/null"))
    ap.add_argument("--out", required=True, type=Path, help="aggregate JSON (all tasks + meta)")
    ap.add_argument("--results-dir", type=Path, default=None,
                    help="if set, ALSO write one score_worker-shaped JSON per task here "
                         "(results/<task_id>.json, the verdict compute-plan's input layout)")
    ap.add_argument("--arms", default="B")
    ap.add_argument("--n-tasks", type=int, default=None, help="score only the first N tasks (debug)")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--device", type=str, default="mps")
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--banked-config-hash", type=str, default=None,
                    help="hash keying the gen log; default = auto-detect from first row (CPU 6dbe47a8)")
    ap.add_argument("--fp16", action="store_true", help="NOT frozen numerics; defaults OFF")
    args = ap.parse_args()

    set_cpu_threads(args.threads)
    from closure_harness.config import CONFIG, config_hash as live_config_hash
    threshold = CONFIG.outcome.assert_threshold
    batch_size = args.batch_size if args.batch_size is not None else CONFIG.nli.batch_size
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())

    if args.fp16:
        _log("[stage2] *** WARNING: --fp16 is NOT the frozen numeric path; use for throughput only.")

    # banked hash: auto-detect from the gen log's first row (the CPU 6dbe47a8 stamp).
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
    gens = index_gens(args.gen_log, banked_hash)
    _log(f"[stage2] {len(tasks)} tasks, arms={arms}, threshold={threshold}, batch_size={batch_size}, "
         f"device={args.device}, banked_hash={banked_hash[:12]}, live_hash={live_config_hash()[:12]}")

    t0 = time.time()
    scorer, det = batched_scorer.build_scorer(args.device)
    _log(f"[stage2] scorer built on {args.device}; warn_only needed: {det['warn_only_used']}")

    pairs, pair_meta, items, per_task = collect_pairs(tasks, gens, pruned, arms)
    n_missing = sum(1 for info in per_task.values() if not info["arms_present"])
    _log(f"[stage2] {len(pairs)} directional pairs over {len(items)} items; "
         f"{n_missing} tasks missing gen (skipped)")

    t_fwd = time.time()
    pair_scores = batched_scorer.score_pairs_batched(scorer, pairs, batch_size, args.fp16)
    fwd_elapsed = time.time() - t_fwd

    item_scalars = reassemble_item_scalars(pair_meta, pair_scores, items, threshold)
    prov = capture_provenance(args.threads, banked_hash,
                              frozen_path="batched_stage2_scorer(score_worker shape)").as_dict()
    prov["device"] = args.device
    prov["batched"] = True
    results = build_task_results(per_task, item_scalars, arms, prov)

    n_per_task_files = 0
    if args.results_dir:
        args.results_dir.mkdir(parents=True, exist_ok=True)
        n_per_task_files = _write_per_task_files(results, args.results_dir)

    elapsed = time.time() - t0
    report = {
        "tool": "batched_stage2_scorer",
        "results": results,
        "meta": {
            "banked_config_hash": banked_hash,
            "live_config_hash": live_config_hash(),
            "device": args.device,
            "warn_only_needed": det["warn_only_used"],
            "batch_size": batch_size,
            "fp16": bool(args.fp16),
            "n_tasks": len(tasks),
            "n_tasks_scored": sum(1 for i in per_task.values() if i["arms_present"]),
            "n_tasks_missing_gen": n_missing,
            "n_items": len(items),
            "pair_count": len(pairs),
            "arms": list(arms),
            "results_dir": str(args.results_dir) if args.results_dir else None,
            "n_per_task_files": n_per_task_files,
            "canonical_ordering": "(task_id, arm, side_rank[change=0,persist=1], item_idx, source_idx, "
                                  "direction[0=(src,claim),1=(claim,src)]); fixed batch_size chunks. "
                                  "NOT the frozen per-__call__ composition — equivalence via "
                                  "batched_stage2_equiv.py.",
            "numerics_source": "score_worker.score_one_task (score_worker.py:53-138) + outcomes.py + "
                               "nli.py; per-conclusion scored once (score()+flag are the same pure call)",
            "elapsed_s": round(elapsed, 1),
            "forward_elapsed_s": round(fwd_elapsed, 1),
            "pairs_per_s": round(len(pairs) / fwd_elapsed, 2) if fwd_elapsed > 0 else None,
        },
    }
    atomic_write_json(args.out, report)
    _log("[stage2] RESULT " + json.dumps({
        "n_tasks_scored": report["meta"]["n_tasks_scored"],
        "n_missing": n_missing, "n_items": len(items), "pair_count": len(pairs),
        "device": args.device, "elapsed_s": report["meta"]["elapsed_s"],
        "pairs_per_s": report["meta"]["pairs_per_s"], "per_task_files": n_per_task_files,
    }))
    _log(f"[stage2] wrote {args.out}")


if __name__ == "__main__":
    main()
