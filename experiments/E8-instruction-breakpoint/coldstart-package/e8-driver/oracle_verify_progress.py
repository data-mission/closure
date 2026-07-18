"""E8 == oracle — INSTRUMENTED COPY of oracle_verify.py (per-sample progress + timestamps).

Identical verdict logic to oracle_verify.py — the re-scoring loop, the per-task strict == compare,
the stratified sample, the fresh-process thread pinning, and the exit codes are UNCHANGED. The ONLY
difference is OBSERVABILITY: every emitted line carries a UTC-ISO timestamp, and the previously
SILENT re-scoring loop now prints a per-sample-task progress line with families... tasks/min rate
and an ETA to completion. This exists because the original oracle's re-scoring loop runs dark for
minutes on a large stratified sample (frac 0.2, min 25/worker) — this copy makes that phase
observable without touching the science. New derived file; original oracle_verify.py byte-untouched.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
from common import set_cpu_threads  # noqa: E402
from score_worker import score_one_task  # noqa: E402  (the SAME frozen-path scorer)


# --------------------------------------------------------------------------- timestamped logging
def _ts() -> str:
    """UTC ISO-8601 second precision, e.g. 2026-07-18T04:40:12Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    """Every log line carries a leading [UTC-ISO] prefix. Log-only — never in the scoring path."""
    print(f"[{_ts()}] {msg}", flush=True)


def _worker_sig(prov: dict) -> str:
    """A signature that changes if a worker ran in a different environment (SEV-4 target)."""
    return "|".join(str(prov.get(k)) for k in
                    ("hostname", "thread_count", "torch_version",
                     "transformers_version", "config_hash"))


def load_results(out_dir: Path) -> dict[str, dict]:
    res = {}
    for p in out_dir.glob("*.json"):
        if p.name.startswith("_"):
            continue
        res[p.stem] = json.loads(p.read_text())
    return res


def stratified_sample(results: dict[str, dict], frac: float, min_per_worker: int,
                      seed: int) -> list[str]:
    """Sample task_ids so every distinct worker-signature has >= min_per_worker sampled (SEV-4)."""
    by_sig: dict[str, list[str]] = defaultdict(list)
    for tid, rec in results.items():
        by_sig[_worker_sig(rec.get("provenance", {}))].append(tid)
    rng = random.Random(seed)
    chosen: set[str] = set()
    for sig, tids in by_sig.items():
        rng.shuffle(tids)
        k = max(min_per_worker, int(len(tids) * frac))
        chosen.update(tids[:min(k, len(tids))])
    return sorted(chosen)


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 per-task == oracle (fresh re-pinned process)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--pruned", type=Path, default=Path("/dev/null"))
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--arms", default="B")
    ap.add_argument("--frac", type=float, default=0.2, help="fraction per worker to re-score")
    ap.add_argument("--min-per-worker", type=int, default=25)
    ap.add_argument("--oracle-threads", type=int, default=1,
                    help="KNOWN-GOOD reference thread count (fresh, != worker default)")
    ap.add_argument("--seed", type=int, default=20260716)
    ap.add_argument("--progress-every", type=int, default=1,
                    help="print a progress line every N sampled tasks (observability only)")
    args = ap.parse_args()

    set_cpu_threads(args.oracle_threads)  # fresh, known-good, BEFORE torch loads
    from closure_harness.config import config_hash
    from closure_harness.nli import NLIScorer

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    tasks = {t["task_id"]: t
             for t in (json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip())}
    from common import load_jsonl, load_pruned
    pruned = load_pruned(args.pruned)
    CH = config_hash()
    gen: dict[tuple[str, str], dict] = {}
    for r in load_jsonl(args.gen_log):
        if r.get("config_hash") == CH and not r.get("error"):
            gen[(r["task_id"], r["arm"])] = r["output"]

    results = load_results(args.out_dir)
    if not results:
        _log("[oracle] no result files to verify")
        sys.exit(1)
    sample = stratified_sample(results, args.frac, args.min_per_worker, args.seed)
    _log(f"[oracle] re-scoring {len(sample)} tasks in a FRESH {args.oracle_threads}-thread "
         f"process; per-task == against parallel results ...")

    scalar = NLIScorer()
    mismatches = []
    t0 = time.time()
    n_total = len(sample)
    for idx, tid in enumerate(sample, 1):
        parallel = results[tid]
        gen_by_arm = {a: gen.get((tid, a)) for a in arms}
        if any(v is None for v in gen_by_arm.values()):
            mismatches.append({"task_id": tid, "reason": "missing generation at oracle time"})
        else:
            fresh = score_one_task(scalar, tasks[tid], gen_by_arm, pruned.get(tid, set()), arms)
            for arm in arms:
                pa, fr = parallel["arms"][arm], fresh["arms"][arm]
                # strict == on the two scored floats (the frozen-path outputs)
                if pa["contamination"] != fr["contamination"] or pa["completeness"] != fr["completeness"]:
                    mismatches.append({
                        "task_id": tid, "arm": arm,
                        "parallel": {"c": pa["contamination"], "k": pa["completeness"]},
                        "fresh": {"c": fr["contamination"], "k": fr["completeness"]},
                        "worker_sig": _worker_sig(parallel.get("provenance", {})),
                    })
        # OBSERVABILITY ONLY (below): rate + ETA over the re-scoring loop; no effect on the verdict.
        if idx % max(1, args.progress_every) == 0 or idx == n_total:
            elapsed_min = (time.time() - t0) / 60.0
            rate = idx / elapsed_min if elapsed_min > 0 else 0.0  # tasks/min
            remaining = n_total - idx
            if rate > 0:
                eta = datetime.fromtimestamp(time.time() + remaining / rate * 60.0, tz=timezone.utc)
                eta_s = eta.strftime("%H:%MZ")
            else:
                eta_s = "??:??Z"
            _log(f"[oracle] {idx}/{n_total} tasks re-scored · {rate:.1f} tasks/min · "
                 f"ETA ~{eta_s} · mismatches so far: {len(mismatches)}")

    dt = time.time() - t0
    by_sig_counts = defaultdict(int)
    for tid in sample:
        by_sig_counts[_worker_sig(results[tid].get("provenance", {}))] += 1
    verdict = "PASS" if not mismatches else "FAIL"
    report = {
        "oracle": "per-task == , fresh re-pinned process",
        "verdict": verdict,
        "oracle_threads": args.oracle_threads,
        "n_sampled_tasks": len(sample),
        "per_worker_coverage": dict(by_sig_counts),
        "n_mismatches": len(mismatches),
        "mismatches": mismatches[:50],
        "elapsed_s": round(dt, 1),
    }
    (args.out_dir / "_oracle_result.json").write_text(json.dumps(report, indent=2))
    _log("[oracle] RESULT " + json.dumps({k: report[k] for k in
         ("verdict", "n_sampled_tasks", "per_worker_coverage", "n_mismatches")}))
    if mismatches:
        _log(f"[oracle] FAIL — {len(mismatches)} per-task mismatches; first 5:")
        for m in mismatches[:5]:
            _log("    " + json.dumps(m))
    sys.exit(0 if verdict == "PASS" else 2)


if __name__ == "__main__":
    main()
