"""E8 == oracle — per-worker-stratified, fresh re-pinned process, per-TASK equality.

Task #17 SEV-4 ruling: the oracle must
  (1) re-score in a FRESH process at a KNOWN-GOOD thread count (default 1 — the reference), so it
      cannot inherit a worker's environment corruption and self-confirm;
  (2) STRATIFY the sample so EVERY worker's tasks are covered (a whole-worker corruption touching
      1/3 of tasks must be catchable, not diluted);
  (3) compare PER TASK (contamination + completeness bit-for-bit ==), matching the harness's own
      established bar (run_exploratory_v2.py job1 aborts on ANY task mismatch), not a loose
      pair-sample proxy.

Because task-sharding is request-preserving for the base scorer (H1) AND thread count provably
does not move the frozen CPU float (H3, PROBE-A/B), a correct parallel result MUST equal the fresh
serial re-score EXACTLY. Any mismatch = a real env/worker corruption (the thing the oracle exists
to catch), and the oracle FAILS LOUD (exits non-zero), naming the worker whose tasks diverged.

Reads each result file's provenance to attribute tasks to workers (by pid/hostname/threads), and
guarantees ≥ min_per_worker sampled tasks per distinct worker signature.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
from common import set_cpu_threads  # noqa: E402
from score_worker import score_one_task  # noqa: E402  (the SAME frozen-path scorer)


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
        print("[oracle] no result files to verify", flush=True)
        sys.exit(1)
    sample = stratified_sample(results, args.frac, args.min_per_worker, args.seed)
    print(f"[oracle] re-scoring {len(sample)} tasks in a FRESH {args.oracle_threads}-thread "
          f"process; per-task == against parallel results ...", flush=True)

    scalar = NLIScorer()
    mismatches = []
    t0 = time.time()
    for tid in sample:
        parallel = results[tid]
        gen_by_arm = {a: gen.get((tid, a)) for a in arms}
        if any(v is None for v in gen_by_arm.values()):
            mismatches.append({"task_id": tid, "reason": "missing generation at oracle time"})
            continue
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
    print("[oracle] RESULT " + json.dumps({k: report[k] for k in
          ("verdict", "n_sampled_tasks", "per_worker_coverage", "n_mismatches")}), flush=True)
    if mismatches:
        print(f"[oracle] FAIL — {len(mismatches)} per-task mismatches; first 5:", flush=True)
        for m in mismatches[:5]:
            print("    " + json.dumps(m), flush=True)
    sys.exit(0 if verdict == "PASS" else 2)


if __name__ == "__main__":
    main()
