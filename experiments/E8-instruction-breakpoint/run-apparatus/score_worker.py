"""E8 scoring worker — task-sharded, thread-pinned, frozen-path-verbatim.

ONE worker = one process. It claims whole probe tasks via file-lock, scores each with the
FROZEN path invoked VERBATIM, and writes one atomic result file per task. Parallelism is ACROSS
whole tasks (task #17 H1: every outcomes.score(scalar, output, ann) call resolves to a
self-contained NLIScorer.__call__ whose bs=16 batch is a pure function of (sources, claim) —
so task-sharding cannot change any score vs serial). NO custom composition, NO re-batching,
NO cache/replay path — the worker calls `outcomes.score` and `NLIScorer` exactly as run_arms.py
phase 3 did (run_arms.py:140-155, the H1 spec).

Frozen-path invariant (SEV-5/SEV-5b ruling): the scorer is the BASE NLIScorer. Under the chosen
m=3 (no long-context axis #1) the segmentation path does NOT enter the freeze (PATCH-NOTES), so
the E8 run uses the same base scorer that produced the banked E5 scores. If a worker imported
SegmentedScorer or any cache path, that would be a DIFFERENT batch composition — forbidden here.

Crash-safety (SEV-7 ruling): per-task lock held until AFTER the atomic result rename; result
written tmp+os.replace; resume skips tasks whose result file already exists.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

# Thread pinning MUST happen before torch loads — do it via common.set_cpu_threads in main().
from common import (  # noqa: E402  (import after arg parse in main; kept here for clarity)
    Provenance,
    atomic_write_json,
    capture_provenance,
    load_jsonl,
    load_pruned,
    set_cpu_threads,
    task_lock,
)


def build_annotations(task: dict, pruned_ids: set[int]):
    """Frozen annotation construction (run_arms.py:141-143 verbatim).

    must_change = the task's must_change items MINUS the pruning register (pre-registered E5
    pruning rule carries to E8); must_persist = all must_persist. Returns closure_harness
    Annotations, imported here so this module has no torch dep until scoring.
    """
    from closure_harness.outcomes import Annotations  # noqa: PLC0415
    keep = [i for i in range(len(task["must_change"])) if i not in pruned_ids]
    return Annotations(
        must_change=tuple(task["must_change"][i] for i in keep),
        must_persist=tuple(task["must_persist"]),
    ), keep


def score_one_task(scalar, task: dict, gen_by_arm: dict[str, dict],
                   pruned_ids: set[int], arms: tuple[str, ...]) -> dict:
    """Score every arm output for one task through the FROZEN path, verbatim.

    scalar        : an NLIScorer instance (the frozen base scorer).
    gen_by_arm    : {arm: output_dict} for this task (the arm-B generation for E8; A/B/C for E5).
    Returns a per-task result dict (one entry per arm) — the exact rec shape of run_arms.py:148.
    """
    # ALL from the frozen outcomes module — score() for the aggregate AND _still_asserts() for
    # the per-item flags (the same frozen call run_exploratory_v2.py:248 used). NOT a custom
    # composition: _still_asserts is outcomes.py's own function at the frozen assert_threshold.
    from closure_harness.outcomes import (  # noqa: PLC0415
        CONFIG as _OC,
        score as frozen_score,
        _still_asserts,
    )
    from closure_harness.schema import parse_output  # noqa: PLC0415

    threshold = _OC.outcome.assert_threshold
    ann, keep = build_annotations(task, pruned_ids)
    per_arm = {}
    for arm in arms:
        o = parse_output(gen_by_arm[arm])            # frozen schema validation
        s = frozen_score(scalar, o, ann)             # FROZEN outcomes.score — verbatim, no wrap
        n = len(ann.must_change)
        # per-item asserted flags, keyed by the ORIGINAL must_change index (keep[j]) so downstream
        # break-aggregation can select verdict_item=true conclusions (task #27 selection rule).
        change_asserted = {
            keep[j]: bool(_still_asserts(scalar, o, concl, threshold))
            for j, concl in enumerate(ann.must_change)
        }
        persist_asserted = [
            bool(_still_asserts(scalar, o, concl, threshold)) for concl in ann.must_persist
        ]
        per_arm[arm] = {
            "n_items": n,
            "contaminated_items": round(s.contamination * n),
            "contamination": s.contamination,
            "completeness": s.completeness,
            "must_change_asserted_by_index": change_asserted,
            "must_persist_asserted": persist_asserted,
        }

    # Carry through the canonical routing fields so downstream break-aggregation can compute the
    # VERDICT-BEARING per-level rate over ONLY verdict_item:true items on break_side (schema-canon
    # + verdict_item addenda). The driver SCORES everything (above) and ROUTES via metadata here;
    # it never reads inside axis_params for scoring. All optional — E5-shaped records omit them.
    ap = task.get("axis_params", {}) if isinstance(task.get("axis_params"), dict) else {}
    break_side = task.get("break_side")
    # break_side item count (the list verdict_item is parallel to). Defaults to must_change when
    # break_side is unset (E5-shaped records).
    break_items = task.get(break_side) if break_side in ("must_change", "must_persist") \
        else task.get("must_change", [])
    n_break = len(break_items) if isinstance(break_items, list) else 0

    # CANON RULING (manager, 2026-07-17): verdict_item ABSENT ⇒ all-true default over the
    # break_side item set (A2's final corpus omits the field — every break_side item is
    # verdict-bearing). Encode the default HERE so it's a rule, not an accident downstream.
    raw_vi = ap.get("verdict_item")
    verdict_item = raw_vi if isinstance(raw_vi, list) else [True] * n_break
    verdict_item_defaulted = not isinstance(raw_vi, list)

    routing = {
        "family_id": task.get("family_id"),
        "axis": task.get("axis"),
        # CANON RULING: dose_level is an INT (1/2/3). Carry as-is; the corpus is authoritative.
        # (Older A1 drafts used "D1"/"D2"/"D3" strings; the final corpus conforms to int.)
        "dose_level": task.get("dose_level"),
        "break_side": break_side,
        # parallel lists over the ORIGINAL (pre-prune) break_side item set: verdict_item[i] and
        # item_roles[i] describe original index i. must_change_asserted_by_index is keyed by the
        # SAME original index (keep[j]), so downstream selects the verdict subset by:
        #   verdict rate = mean over {i : verdict_item[i] and i in kept_change_indices}
        #                   of must_change_asserted_by_index[i]        (when break_side==must_change)
        # A verdict_item:true index that was pruned is absent from the scored set — aggregation
        # must treat that as a corpus-construction issue, not silently score it.
        "verdict_item": verdict_item,
        "verdict_item_defaulted": verdict_item_defaulted,  # true = field absent, all-true applied
        "item_roles": ap.get("item_roles"),
    }
    return {
        "task_id": task["task_id"],
        "kept_change_indices": keep,
        "routing": routing,
        "arms": per_arm,
    }


def run_worker(
    tasks_path: Path,
    gen_log_path: Path,
    pruned_path: Path,
    out_dir: Path,
    lock_dir: Path,
    threads: int,
    arms: tuple[str, ...],
    config_hash_expected: str | None,
    max_tasks: int | None = None,
) -> dict:
    """Claim-and-score loop. Returns a summary dict (tasks scored, skipped, elapsed)."""
    from closure_harness.config import config_hash  # noqa: PLC0415
    from closure_harness.nli import NLIScorer  # noqa: PLC0415

    CH = config_hash()
    if config_hash_expected and CH != config_hash_expected:
        raise SystemExit(
            f"CONFIG HASH MISMATCH: live {CH} != expected {config_hash_expected}. "
            "Refusing to score under an unregistered config."
        )

    prov: Provenance = capture_provenance(threads, CH)
    tasks = [json.loads(l) for l in tasks_path.read_text().splitlines() if l.strip()]
    if max_tasks:
        tasks = tasks[:max_tasks]

    # pruning register (per-task set of must_change indices to drop)
    pruned = load_pruned(pruned_path)

    # generations: latest clean row per (task_id, arm) matching config_hash, no error
    gen: dict[tuple[str, str], dict] = {}
    for r in load_jsonl(gen_log_path):
        if r.get("config_hash") == CH and not r.get("error"):
            gen[(r["task_id"], r["arm"])] = r["output"]

    scalar = NLIScorer()  # ONE frozen scorer per process (base path, no segmentation, no cache)
    t0 = time.time()
    n_scored = n_skipped = n_missing = 0

    for task in tasks:
        tid = task["task_id"]
        result_path = out_dir / f"{tid}.json"
        if result_path.exists():
            n_skipped += 1
            continue
        gen_by_arm = {a: gen.get((tid, a)) for a in arms}
        if any(v is None for v in gen_by_arm.values()):
            n_missing += 1
            continue  # generation not ready for this task/arm yet; a later pass will get it

        # LOCK held across the score + write + rename (SEV-7 #4: mutual exclusion until rename)
        with task_lock(lock_dir, tid) as fd:
            if fd is None:
                n_skipped += 1
                continue
            if result_path.exists():  # re-check under lock (another worker finished it)
                n_skipped += 1
                continue
            rec = score_one_task(scalar, task, gen_by_arm, pruned.get(tid, set()), arms)
            rec["provenance"] = prov.as_dict()
            rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            atomic_write_json(result_path, rec)  # tmp + os.replace, still inside the lock
            n_scored += 1

    dt = time.time() - t0
    return {
        "worker_threads": threads,
        "tasks_scored": n_scored,
        "tasks_skipped": n_skipped,
        "tasks_missing_gen": n_missing,
        "elapsed_s": round(dt, 2),
        "pairs_per_s_note": "task-rate not pair-rate; calibration reports pair-rate",
        "provenance": prov.as_dict(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 scoring worker (task-sharded, frozen path)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--pruned", type=Path, default=Path("/dev/null"))
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--lock-dir", required=True, type=Path)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--arms", default="B", help="comma-separated arm ids to score (E8: B)")
    ap.add_argument("--config-hash", default=None, help="abort if live config hash differs")
    ap.add_argument("--max-tasks", type=int, default=None)
    args = ap.parse_args()

    set_cpu_threads(args.threads)  # BEFORE any torch op
    summary = run_worker(
        tasks_path=args.tasks,
        gen_log_path=args.gen_log,
        pruned_path=args.pruned,
        out_dir=args.out_dir,
        lock_dir=args.lock_dir,
        threads=args.threads,
        arms=tuple(a.strip() for a in args.arms.split(",") if a.strip()),
        config_hash_expected=args.config_hash,
        max_tasks=args.max_tasks,
    )
    print("[worker] " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
