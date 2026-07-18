"""E8 A-dependency FILTER — PROCESS-PARALLEL scoring wrapper (NEW; wraps filter_stage.py).

Same result as filter_stage.py's SCORING phase, BY CONSTRUCTION, but sharded across N worker
processes instead of one serial process. Generation is NOT done here — this consumes an existing
--gen-log (the banked draws) and produces the identical pruned-items.json + filter-report.json.

WHY THIS IS REQUEST-PRESERVING (== serial):
  filter_stage.score_draws scores every draw independently: for each family it reads only that
  family's top-level task record + its own generated outputs, and each _still_asserts(scalar, o,
  concl, threshold) call is a pure function of (output, conclusion, threshold) with a frozen NLI
  path. There is NO cross-family or cross-draw state. So partitioning the family list across
  processes, each running the IDENTICAL per-call path with the SAME per-worker torch thread count
  (2), yields per-item booleans identical to serial. We do NOT reimplement scoring: the per-family
  loop below is byte-for-byte the body of filter_stage.score_draws' inner loop, and the final
  pruning/exclusion decision is filter_stage.adjudicate VERBATIM.

THREAD COUNT: each worker sets threads=2 (filter_stage.set_cpu_threads). Do NOT raise this per
worker — torch reduction order depends on thread count and can flip a borderline score at the
0.7 assert threshold. Parallelism is across PROCESSES (families), not threads.

Zero model spend: scoring is CPU NLI only, no API key touched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
# Import the UNTOUCHED originals — we reuse, never reimplement.
import filter_stage  # noqa: E402
from common import atomic_write_json, load_jsonl, set_cpu_threads  # noqa: E402


# --------------------------------------------------------------------------- timestamped logging
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ts() -> str:
    """UTC ISO-8601 second precision, e.g. 2026-07-18T03:40:12Z."""
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    """Every log line carries a leading [UTC-ISO] prefix. Log-only — never in the scoring path."""
    print(f"[{_ts()}] {msg}", flush=True)


# --------------------------------------------------------------------------- deterministic shard
def shard_families(family_ids: list[str], n_shards: int) -> list[list[str]]:
    """Round-robin the SORTED family ids across n_shards. Deterministic: shard membership depends
    only on (sorted ids, n_shards), never on dict/order or timing. Every family lands in exactly
    one shard; union == all families."""
    ordered = sorted(family_ids)
    shards: list[list[str]] = [[] for _ in range(n_shards)]
    for i, fam in enumerate(ordered):
        shards[i % n_shards].append(fam)
    return shards


# --------------------------------------------------------------------------- per-shard scoring
def _index_gens(gen_log: Path, config_hash: str) -> dict:
    """(task_id, filter_state, draw_index) -> output. IDENTICAL selection to
    filter_stage.score_draws: config_hash match, no error, filter_state present."""
    gens: dict[tuple, dict] = {}
    for r in load_jsonl(gen_log):
        if r.get("config_hash") == config_hash and not r.get("error") and "filter_state" in r:
            gens[(r["task_id"], r["filter_state"], r["draw_index"])] = r["output"]
    return gens


def score_families(fam_ids: list[str], top: dict, gens: dict, threshold: float, n_draws: int,
                   scorer, worker_tag: str = "", progress_cb=None) -> dict:
    """Score a SUBSET of families. The body of this per-family loop is byte-identical to
    filter_stage.score_draws' inner loop (same parse_output, same _still_asserts(scalar,...),
    same 'a'/'c' keying, same n_draws range, same None-skip). Returns {family_id: per_item}
    in the exact shape score_draws returns for those families.

    `scorer` is a live NLIScorer (the worker's own instance). We import parse_output/_still_asserts
    from the frozen harness — the same modules score_draws imports."""
    from closure_harness.schema import parse_output
    from closure_harness.outcomes import _still_asserts

    out: dict[str, dict] = {}
    total = len(fam_ids)
    for i, fam in enumerate(fam_ids, 1):
        task = top[fam]
        mc = task["must_change"]
        per_item = {i2: {"a": [], "c": []} for i2 in range(len(mc))}
        for state, key in (("assumption", "a"), ("correction", "c")):
            for d in range(n_draws):
                g = gens.get((task["task_id"], state, d))
                if g is None:
                    continue
                o = parse_output(g)
                for i2, concl in enumerate(mc):
                    per_item[i2][key].append(bool(_still_asserts(scorer, o, concl, threshold)))
        out[fam] = per_item
        _log(f"[filter-score {worker_tag}] {i}/{total} families")
        if progress_cb is not None:
            progress_cb(i, total)  # observability only — never read by merge/adjudicate
    return out


# --------------------------------------------------------------------------- worker entrypoint
def _run_worker(args_ns) -> None:
    """Worker mode: score this shard's families, write ONE atomic partial JSON. Resumable at the
    parent level (parent skips a shard whose complete file already exists)."""
    # set_cpu_threads MUST run before the first torch op (same ordering as filter_stage.main()).
    set_cpu_threads(args_ns.threads)
    from closure_harness.config import CONFIG, config_hash
    from closure_harness.nli import NLIScorer

    CH = config_hash()
    if args_ns.config_hash and CH != args_ns.config_hash:
        raise SystemExit(f"config_hash drift: worker={CH} parent={args_ns.config_hash}")
    threshold = CONFIG.outcome.assert_threshold

    tasks = [json.loads(l) for l in args_ns.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)
    all_ids = sorted(top.keys())
    shards = shard_families(all_ids, args_ns.workers)
    fam_ids = shards[args_ns.shard_index]

    gens = _index_gens(args_ns.gen_log, CH)
    scorer = NLIScorer()
    tag = f"w{args_ns.shard_index}"

    # Live per-family progress file (observability ONLY): the parent sums these to report a
    # smooth "total X/N" + rate/ETA instead of jumping shard-sized. Never read by merge/adjudicate
    # — those consume only the final scored-shard-K.json. Written atomically so a mid-write read
    # by the parent never sees a torn count.
    progress_path = args_ns.out_dir / f"scored-shard-{args_ns.shard_index}.progress"

    def _emit_progress(done: int, total: int) -> None:
        atomic_write_json(progress_path, {"shard_index": args_ns.shard_index,
                                          "done": done, "total": total, "config_hash": CH})

    scored = score_families(fam_ids, top, gens, threshold, args_ns.n_draws, scorer, tag,
                            progress_cb=_emit_progress)

    # Persist WITH the family list so the parent can verify completeness before trusting it.
    shard_path = args_ns.out_dir / f"scored-shard-{args_ns.shard_index}.json"
    payload = {"shard_index": args_ns.shard_index, "n_workers": args_ns.workers,
               "config_hash": CH, "family_ids": fam_ids,
               # per_item dicts have int keys; JSON-stringifies them, parent re-ints on merge.
               "scored": scored}
    atomic_write_json(shard_path, payload)
    _log(f"[filter-score {tag}] DONE wrote {shard_path.name} ({len(scored)} families)")


# --------------------------------------------------------------------------- shard load + merge
def _load_complete_shard(path: Path, expected_fams: list[str], CH: str):
    """Return the scored dict for a shard IFF the file exists, matches config_hash, and covers
    exactly its expected families. Else None (parent (re)runs that shard)."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if payload.get("config_hash") != CH:
        return None
    if sorted(payload.get("family_ids", [])) != sorted(expected_fams):
        return None
    scored_raw = payload.get("scored", {})
    if sorted(scored_raw.keys()) != sorted(expected_fams):
        return None
    # re-int the item-index keys that JSON stringified
    scored: dict[str, dict] = {}
    for fam, per_item in scored_raw.items():
        scored[fam] = {int(i): ac for i, ac in per_item.items()}
    return scored


# --------------------------------------------------------------------------- parent orchestration
def _spawn_worker(args_ns, shard_index: int):
    import subprocess
    cmd = [sys.executable, str(Path(__file__).resolve()),
           "--tasks", str(args_ns.tasks), "--gen-log", str(args_ns.gen_log),
           "--out-dir", str(args_ns.out_dir), "--template", str(args_ns.template),
           "--arm-b-instruction", str(args_ns.arm_b_instruction),
           "--n-draws", str(args_ns.n_draws), "--threads", str(args_ns.threads),
           "--workers", str(args_ns.workers), "--config-hash", args_ns._ch,
           "--_worker", "--_shard-index", str(shard_index)]
    if args_ns.allow_unpinned_instruction:
        cmd.append("--allow-unpinned-instruction")
    return subprocess.Popen(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 A-dependency filter — PROCESS-PARALLEL scorer")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--arm-b-instruction", type=Path, required=True)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--threads", type=int, default=2, help="per-worker torch threads (KEEP 2)")
    ap.add_argument("--workers", type=int, default=4, help="parallel scoring processes")
    ap.add_argument("--config-hash", default="", help="expected config_hash (drift guard)")
    ap.add_argument("--allow-unpinned-instruction", action="store_true")
    # internal worker-mode flags
    ap.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--_shard-index", dest="shard_index", type=int, default=0,
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.threads != 2:
        _log(f"[filter-score] WARNING threads={args.threads} != 2; borderline scores at the "
             "assert threshold may diverge from the frozen serial path.")

    # WORKER MODE ------------------------------------------------------------
    if args._worker:
        _run_worker(args)
        return

    # PARENT MODE ------------------------------------------------------------
    # Pin the ARM-B instruction hash exactly as filter_stage.main does (parity; no gen here but we
    # keep the same registration gate so an unpinned instruction can't silently slip through).
    import hashlib
    ARMB_PINNED = "f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c"
    armb_bytes = args.arm_b_instruction.read_bytes()
    if hashlib.sha256(armb_bytes).hexdigest() != ARMB_PINNED and not args.allow_unpinned_instruction:
        raise SystemExit("ARM-B instruction hash mismatch; refusing (see filter_stage).")

    # Resolve config_hash the SAME way filter_stage does; hold it for workers + drift guard.
    set_cpu_threads(args.threads)
    from closure_harness.config import CONFIG, config_hash
    CH = config_hash()
    if args.config_hash and args.config_hash != CH:
        raise SystemExit(f"--config-hash {args.config_hash} != live {CH}")
    args._ch = CH
    threshold = CONFIG.outcome.assert_threshold

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    all_ids = sorted(top.keys())
    shards = shard_families(all_ids, args.workers)
    n_fams = len(all_ids)
    _log(f"[filter-score] {n_fams} families across {args.workers} workers "
         f"(threads={args.threads}/worker); config_hash={CH[:12]}")

    t0 = time.time()
    # Count families already done in complete shards (resume) — they're NOT scored this run, so
    # they must be excluded from the families/min rate (which measures THIS run's throughput).
    resumed_done = 0
    # Resume: figure out which shards still need running.
    procs = {}
    for k in range(args.workers):
        shard_path = args.out_dir / f"scored-shard-{k}.json"
        if _load_complete_shard(shard_path, shards[k], CH) is not None:
            resumed_done += len(shards[k])
            _log(f"[filter-score] shard {k} already complete ({len(shards[k])} fams) — skip")
            continue
        procs[k] = _spawn_worker(args, k)

    # Wait, printing a merged progress line every 30s from the shard files on disk. The line also
    # reports families/min for THIS run (done-this-run / elapsed) and an ETA to completion at that
    # rate. Rate excludes resumed families so it reflects real live throughput, not skipped work.
    last_report = 0.0
    while procs:
        for k, p in list(procs.items()):
            if p.poll() is not None:
                if p.returncode != 0:
                    raise SystemExit(f"[filter-score] worker shard {k} exited {p.returncode}")
                del procs[k]
        now = time.time()
        if now - last_report >= 30 and procs:
            # Live count: prefer the definitive completed-shard count; else the worker's live
            # .progress file (updated per family). This makes "total X/N" move smoothly per family
            # instead of jumping shard-sized. Both are observability — merge reads only the .json.
            done = 0
            for k in range(args.workers):
                sp = args.out_dir / f"scored-shard-{k}.json"
                s = _load_complete_shard(sp, shards[k], CH)
                if s is not None:
                    done += len(s)
                    continue
                pp = args.out_dir / f"scored-shard-{k}.progress"
                try:
                    prog = json.loads(pp.read_text())
                    if prog.get("config_hash") == CH:
                        done += int(prog.get("done", 0))
                except (FileNotFoundError, OSError, json.JSONDecodeError, ValueError, TypeError):
                    pass  # no progress yet for this shard (worker still loading model)
            done_this_run = max(0, done - resumed_done)
            elapsed_min = (now - t0) / 60.0
            rate = done_this_run / elapsed_min if elapsed_min > 0 else 0.0  # families/min
            remaining = n_fams - done
            if rate > 0:
                eta_dt = datetime.fromtimestamp(now + remaining / rate * 60.0, tz=timezone.utc)
                eta_s = eta_dt.strftime("%H:%MZ")
            else:
                eta_s = "??:??Z"
            _log(f"[filter-score] {done}/{n_fams} total · {rate:.1f} fam/min · ETA ~{eta_s} "
                 f"(running shards: {sorted(procs)})")
            last_report = now
        if procs:
            time.sleep(2)

    # Merge every shard into the exact dict shape score_draws returns.
    scored: dict[str, dict] = {}
    for k in range(args.workers):
        shard_path = args.out_dir / f"scored-shard-{k}.json"
        s = _load_complete_shard(shard_path, shards[k], CH)
        if s is None:
            raise SystemExit(f"[filter-score] shard {k} missing/incomplete after run")
        overlap = set(s) & set(scored)
        if overlap:
            raise SystemExit(f"[filter-score] family overlap across shards: {overlap}")
        scored.update(s)
    if sorted(scored.keys()) != all_ids:
        missing = set(all_ids) - set(scored)
        raise SystemExit(f"[filter-score] merged scoring missing families: {missing}")

    # Adjudicate VERBATIM via the untouched original — same pruning/exclusion decision as serial.
    passed, excluded, pruned_rows, per_family = filter_stage.adjudicate(top, scored, args.n_draws)

    # Emit pruned-items.json + filter-report.json in the SAME format filter_stage.main writes.
    atomic_write_json(args.out_dir / "pruned-items.json", pruned_rows)
    report = {
        "stage": "A-dependency-filter", "config_hash": CH,
        "ruling_confirmations": {
            "A3_assumption_state": "withhold ALL axis_params.corrections[] (base world, A intact, "
                                   "no corrections applied); filter tests the flip between base "
                                   "and FULLY-corrected states",
            "A2_assumption_state": "withhold the endorsement SOURCES at "
                                   "axis_params.scoped_exceptions[].source_id (rule-without-"
                                   "exception world)",
            "A1_assumption_state": "withhold the not_A_evidence document",
            "top_level_selection": "max dose_level record per family (uniform across axes; A2 top "
                                   "= max scoped-exception level)",
            "confirmed_by": "team-lead 2026-07-17",
        },
        "n_families": len(top), "n_passed": len(passed), "n_excluded": len(excluded),
        "n_draws_per_state": args.n_draws, "assert_threshold": threshold,
        "passed_families": passed, "excluded_families": excluded,
        "n_pruned_items": len(pruned_rows),
        "per_family": per_family,
        "elapsed_s": round(time.time() - t0, 1),
    }
    atomic_write_json(args.out_dir / "filter-report.json", report)
    _log("[filter] RESULT " + json.dumps({k: report[k] for k in
         ("n_families", "n_passed", "n_excluded", "n_pruned_items")}))
    _log(f"[filter] wrote pruned-items.json ({len(pruned_rows)} rows) + filter-report.json "
         f"(parallel, {args.workers} workers, {round(time.time()-t0,1)}s)")


if __name__ == "__main__":
    main()
