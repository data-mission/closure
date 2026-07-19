"""E8 scoring orchestrator — calibration + worker autotune + scheduled parallel run.

Replaces ALL promised throughput numbers with a MEASURED schedule (task #17 SEV-1 ruling):

STAGE 1 — CALIBRATION (fixed wall budget, default 10 min).
  Score a STRATIFIED sample of tasks with ONE thread-pinned worker and MEASURE the real
  pairs/s + tasks/s on THIS machine, THIS corpus. Print the real schedule (tasks, est. wall
  time at 1 worker). No number is promised; every number printed is measured here.

STAGE 2 — WORKER AUTOTUNE (SEV-2 ruling).
  Start with 2 workers. Measure aggregate tasks/s over a probe window. Add a 3rd worker ONLY if
  aggregate improves >= AUTOTUNE_GAIN (default 1.5x) vs 1 worker. THERMAL GUARD: if aggregate
  throughput decays > THERMAL_DECAY (default 20%) over THERMAL_WINDOW (default 30 min), drop a
  worker. Re-measure after each change. The machine's real sustained rate governs, not a claim.

STAGE 3 — RUN TO COMPLETION.
  Spawn the chosen worker count; each is score_worker.run_worker in its own process, task-locked,
  atomic-writing, resumable. Orchestrator monitors, applies the thermal guard, and re-launches a
  worker that exits early while tasks remain.

Each worker is a SEPARATE process (true parallelism past the GIL for CPU-bound torch). The
orchestrator itself does no scoring — it spawns, measures, and schedules. All scoring is the
frozen path verbatim (score_worker).
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

DRIVER = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- stratified sample
def stratified_task_ids(tasks: list[dict], k: int) -> list[str]:
    """Pick k tasks spread across the difficulty axes so calibration sees the real cost tail.

    Strata: by number of sources (drives pairs/call) and by must_change count (drives calls/task).
    We sort by (n_sources, n_must_change) and take an even stride so the sample spans light and
    heavy tasks — calibration on only-light tasks would under-estimate wall time (SEV-1's tail).
    """
    def weight(t):
        nsrc = len(t.get("sources", [])) + (1 if t.get("not_A_evidence") else 0)
        return (nsrc, len(t.get("must_change", [])) + len(t.get("must_persist", [])))
    ordered = sorted(tasks, key=weight)
    if k >= len(ordered):
        return [t["task_id"] for t in ordered]
    stride = len(ordered) / k
    return [ordered[int(i * stride)]["task_id"] for i in range(k)]


# --------------------------------------------------------------------------- worker process
def _worker_entry(kwargs: dict) -> None:
    """Child-process entry: pin threads, then run the frozen-path worker to completion."""
    import sys
    sys.path.insert(0, str(DRIVER))
    from common import set_cpu_threads
    from score_worker import run_worker
    set_cpu_threads(kwargs.pop("threads_pin"))
    summary = run_worker(**kwargs)
    (kwargs["out_dir"] / f"_worker_summary_{mp.current_process().pid}.json").write_text(
        json.dumps(summary)
    )


def _spawn_worker(worker_kwargs: dict, threads: int) -> mp.Process:
    kw = dict(worker_kwargs)
    kw["threads"] = threads
    kw["threads_pin"] = threads
    p = mp.Process(target=_worker_entry, args=(kw,), daemon=False)
    p.start()
    return p


def _count_results(out_dir: Path) -> int:
    return len([p for p in out_dir.glob("*.json") if not p.name.startswith("_worker_summary")])


def _measure_rate(out_dir: Path, worker_kwargs: dict, n_workers: int, threads: int,
                  window_s: float) -> float:
    """Spawn n_workers for window_s, return tasks/s aggregate (then stop them)."""
    before = _count_results(out_dir)
    procs = [_spawn_worker(worker_kwargs, threads) for _ in range(n_workers)]
    t0 = time.time()
    while time.time() - t0 < window_s and any(p.is_alive() for p in procs):
        time.sleep(1.0)
    for p in procs:
        if p.is_alive():
            p.terminate()
    for p in procs:
        p.join(timeout=10)
    dt = time.time() - t0
    done = _count_results(out_dir) - before
    return done / dt if dt else 0.0


# --------------------------------------------------------------------------- stages
def calibrate(tasks: list[dict], worker_kwargs: dict, threads: int, budget_s: float) -> dict:
    """STAGE 1: one worker, measure real tasks/s + pairs/s over a fixed wall budget."""
    sample_k = max(3, len(tasks) // 10)
    sample_ids = set(stratified_task_ids(tasks, sample_k))
    cal_kwargs = dict(worker_kwargs)
    cal_kwargs["max_tasks"] = None
    # restrict the worker to the calibration sample via a temp tasks file
    cal_tasks = [t for t in tasks if t["task_id"] in sample_ids]
    cal_tasks_path = worker_kwargs["out_dir"].parent / "_calibration_tasks.jsonl"
    cal_tasks_path.write_text("\n".join(json.dumps(t) for t in cal_tasks) + "\n")
    cal_kwargs["tasks_path"] = cal_tasks_path

    print(f"[calibrate] 1 worker, {threads} threads, {len(cal_tasks)} stratified tasks, "
          f"budget {budget_s:.0f}s ...", flush=True)
    before = _count_results(worker_kwargs["out_dir"])
    p = _spawn_worker(cal_kwargs, threads)
    t0 = time.time()
    while p.is_alive() and time.time() - t0 < budget_s:
        time.sleep(1.0)
    if p.is_alive():
        p.terminate(); p.join(timeout=10)
    dt = time.time() - t0
    done = _count_results(worker_kwargs["out_dir"]) - before
    rate = done / dt if dt else 0.0
    total = len(tasks)
    est_1w_s = (total / rate) if rate else float("inf")
    result = {
        "stage": "calibration",
        "threads": threads,
        "sample_tasks": len(cal_tasks),
        "tasks_scored_in_budget": done,
        "budget_s": budget_s,
        "measured_tasks_per_s_1worker": round(rate, 4),
        "corpus_total_tasks": total,
        "est_wall_s_1worker": round(est_1w_s, 1) if rate else None,
        "est_wall_h_1worker": round(est_1w_s / 3600, 2) if rate else None,
    }
    print("[calibrate] RESULT " + json.dumps(result), flush=True)
    if rate == 0:
        print("[calibrate] WARNING: zero tasks scored in budget — box saturated or corpus empty; "
              "schedule is unknown, NOT extrapolated.", flush=True)
    return result


def autotune(worker_kwargs: dict, threads: int, gain: float, probe_s: float) -> int:
    """STAGE 2: measure 1 vs 2 (vs 3) workers; return the chosen worker count."""
    print(f"[autotune] probing worker counts (gain gate {gain}x, {probe_s:.0f}s probes) ...",
          flush=True)
    r1 = _measure_rate(worker_kwargs["out_dir"], worker_kwargs, 1, threads, probe_s)
    r2 = _measure_rate(worker_kwargs["out_dir"], worker_kwargs, 2, threads, probe_s)
    print(f"[autotune] 1w={r1:.3f} t/s, 2w={r2:.3f} t/s "
          f"(2w gain {r2/r1 if r1 else 0:.2f}x)", flush=True)
    chosen = 2 if (r1 and r2 / r1 >= gain) else 1
    if chosen == 2:
        r3 = _measure_rate(worker_kwargs["out_dir"], worker_kwargs, 3, threads, probe_s)
        print(f"[autotune] 3w={r3:.3f} t/s (vs 2w {r2:.3f}, gain {r3/r2 if r2 else 0:.2f}x)",
              flush=True)
        if r2 and r3 / r2 >= gain:
            chosen = 3
    print(f"[autotune] CHOSEN worker count: {chosen}", flush=True)
    return chosen


def run_to_completion(tasks: list[dict], worker_kwargs: dict, n_workers: int, threads: int,
                      thermal_decay: float, thermal_window_s: float) -> None:
    """STAGE 3: run n_workers to completion with thermal guard + relaunch."""
    total = len(tasks)
    print(f"[run] {n_workers} workers × {threads} threads → {total} tasks", flush=True)
    procs = [_spawn_worker(worker_kwargs, threads) for _ in range(n_workers)]
    last_check = time.time()
    last_done = _count_results(worker_kwargs["out_dir"])
    last_rate = None
    while True:
        done = _count_results(worker_kwargs["out_dir"])
        if done >= total:
            print(f"[run] complete: {min(done, total)}/{total} tasks scored "
                  f"(calibration/autotune pre-scored some; resume skips them)", flush=True)
            break
        # relaunch any worker that exited while tasks remain (crash/early-exit resume)
        for i, p in enumerate(procs):
            if not p.is_alive():
                procs[i] = _spawn_worker(worker_kwargs, threads)
        # thermal guard
        now = time.time()
        if now - last_check >= thermal_window_s:
            rate = (done - last_done) / (now - last_check)
            if last_rate and rate < last_rate * (1 - thermal_decay) and n_workers > 1:
                n_workers -= 1
                print(f"[run] THERMAL GUARD: throughput {rate:.3f} < "
                      f"{last_rate:.3f}×(1-{thermal_decay}); dropping to {n_workers} workers",
                      flush=True)
                if procs and procs[-1].is_alive():
                    procs[-1].terminate()
                procs = procs[:n_workers]
            last_rate, last_done, last_check = rate, done, now
            print(f"[run] progress {done}/{total} ({rate:.3f} t/s, {n_workers}w)", flush=True)
        time.sleep(5.0)
    for p in procs:
        if p.is_alive():
            p.join(timeout=30)


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="E8 calibrate + autotune + run orchestrator")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--pruned", type=Path, default=Path("/dev/null"))
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--lock-dir", required=True, type=Path)
    ap.add_argument("--threads", type=int, default=2, help="threads per worker (SEV-2: 2)")
    ap.add_argument("--arms", default="B")
    ap.add_argument("--config-hash", default=None)
    ap.add_argument("--calibration-s", type=float, default=600.0, help="10-min default")
    ap.add_argument("--autotune-gain", type=float, default=1.5)
    ap.add_argument("--autotune-probe-s", type=float, default=120.0)
    ap.add_argument("--thermal-decay", type=float, default=0.20)
    ap.add_argument("--thermal-window-s", type=float, default=1800.0, help="30 min")
    ap.add_argument("--skip-calibration", action="store_true",
                    help="dry-run/testing only; production always calibrates")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.lock_dir.mkdir(parents=True, exist_ok=True)
    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]

    worker_kwargs = dict(
        tasks_path=args.tasks, gen_log_path=args.gen_log, pruned_path=args.pruned,
        out_dir=args.out_dir, lock_dir=args.lock_dir, threads=args.threads,
        arms=tuple(a.strip() for a in args.arms.split(",") if a.strip()),
        config_hash_expected=args.config_hash, max_tasks=None,
    )

    if not args.skip_calibration:
        cal = calibrate(tasks, worker_kwargs, args.threads, args.calibration_s)
        (args.out_dir / "_calibration.json").write_text(json.dumps(cal, indent=2))

    n_workers = autotune(worker_kwargs, args.threads, args.autotune_gain, args.autotune_probe_s)
    run_to_completion(tasks, worker_kwargs, n_workers, args.threads,
                      args.thermal_decay, args.thermal_window_s)
    print("[orchestrator] scoring complete. Run the oracle next (oracle_verify.py).", flush=True)


if __name__ == "__main__":
    main()
