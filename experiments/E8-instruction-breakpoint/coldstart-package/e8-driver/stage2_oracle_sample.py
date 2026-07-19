"""E8 Stage-2 GPU-path ORACLE — bounded stratified CPU cross-check (Option C, §5 validity gate).

Closes the verdict-plan §5 gap for GPU-scored Stage-2: the compute plan requires
~/e8-run/<axis>-filter/results/_oracle_result.json (PASS/FAIL) and blocks an axis's break_verdict on
FAIL. The registered oracle (oracle_verify.py) re-scores a stratified sample in a FRESH 1-thread CPU
process and demands per-task == vs the result files — that IS the instrument-identity check §5 wants.
The batched GPU scorer never runs it. This tool runs it, BOUNDED, WITHOUT modifying oracle_verify.py.

WHY BOUNDED + WHY A DERIVED INPUT (both team-lead constraints, both mechanism-verified):
- oracle_verify samples INTERNALLY via stratified_sample(results, frac, min_per_worker, seed) over
  whatever *.json files are in --out-dir, stratified by WORKER SIGNATURE (hostname|threads|versions|
  config_hash). The GPU batched results all share ONE signature (single MPS process), so its native
  stratification would pick max(min_per_worker, frac*N) of the FULL corpus — the 40-hour-instrument
  trap. It has NO task-list flag. So we cannot ask it for "these 12 tasks".
- MECHANISM (verified): oracle_verify globs --out-dir for *.json. We stage ONLY our chosen ~N sampled
  <task_id>.json files into a temp dir and run oracle_verify --out-dir <tempdir> --frac 1.0. With one
  worker-sig bucket and frac=1.0, k=int(N*1.0)=N → it re-scores EXACTLY our sample, on fresh CPU
  1-thread. oracle_verify.py stays BYTE-UNCHANGED (imports/subprocess only).

SAMPLE (team-lead spec): ~12 tasks/axis, stratified to cover every (dose_level × break_side) cell
PRESENT in the results, PLUS force-include any task with contamination>0 or a defaulted verdict_item,
up to the cap. Keeps the CPU leg ~3-6 min/axis at the measured ~6-18 s/call.

DISCLOSURE (team-lead spec): the emitted _oracle_result.json carries the sample composition (task_ids,
per-stratum counts, n/total) and a "gpu-path oracle = stratified CPU cross-check" note, so §5's
consumer knows exactly what PASSed (a fresh-CPU per-task re-score of a bounded stratified sample of
the GPU results — NOT a full-corpus re-score, NOT the multi-worker-corruption check the registered
CPU-fleet oracle ran).

SEQUENCE (in run_stage2_gpu.sh): equiv gate → scored pass → THIS oracle sample gate. Any mismatch =
loud FAIL, nonzero exit, axis verdict blocked — never auto-continue.

CLI:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/stage2_oracle_sample.py \
      --tasks <corpus-candidates/<axis>.jsonl> --gen-log ~/e8-run/<axis>-stage2/stage2-gen.jsonl \
      --pruned ~/e8-run/<axis>-filter/pruned-items.json \
      --results-dir ~/e8-run/<axis>-stage2/results \
      --sample-cap 12 --arms B
  echo "exit=$?"   # nonzero => oracle FAIL => axis verdict blocked
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def load_results(results_dir: Path) -> dict:
    """Same selection as oracle_verify.load_results: *.json, skip _-prefixed (the trap)."""
    res = {}
    for p in results_dir.glob("*.json"):
        if p.name.startswith("_"):
            continue
        res[p.stem] = json.loads(p.read_text())
    return res


def choose_sample(results: dict, cap: int) -> tuple[list[str], dict]:
    """Stratified pick of <= cap task_ids. Strategy (deterministic, sorted for reproducibility):
      1. FORCE-INCLUDE any task with contamination>0 (any arm) or verdict_item_defaulted=True — these
         are the highest-value cross-check targets (a contaminated item or a defaulted routing rule is
         exactly where a scoring divergence would matter).
      2. Then COVER every (dose_level, break_side) cell present: add one representative per uncovered
         cell (sorted task_id) until cap or all cells covered.
      3. Then round-robin fill remaining cap across cells (sorted) for headroom.
    Returns (sorted sample task_ids, strata report)."""
    def cell(rec):
        r = rec.get("routing", {})
        return (r.get("dose_level"), r.get("break_side"))

    def contaminated(rec):
        for arm in rec.get("arms", {}).values():
            if (arm.get("contamination") or 0) > 0:
                return True
        return False

    def defaulted(rec):
        return bool(rec.get("routing", {}).get("verdict_item_defaulted"))

    all_ids = sorted(results.keys())
    chosen: list[str] = []
    chosen_set: set[str] = set()

    # 1. forced
    forced = [t for t in all_ids if contaminated(results[t]) or defaulted(results[t])]
    for t in forced:
        if len(chosen) >= cap:
            break
        if t not in chosen_set:
            chosen.append(t); chosen_set.add(t)

    # 2. cell coverage
    by_cell: dict[tuple, list[str]] = {}
    for t in all_ids:
        by_cell.setdefault(cell(results[t]), []).append(t)
    for c in sorted(by_cell.keys(), key=lambda x: (str(x[0]), str(x[1]))):
        if len(chosen) >= cap:
            break
        # is this cell already covered by a forced pick?
        if any(cell(results[t]) == c for t in chosen):
            continue
        for t in by_cell[c]:
            if t not in chosen_set:
                chosen.append(t); chosen_set.add(t)
                break

    # 3. round-robin fill
    cells_sorted = sorted(by_cell.keys(), key=lambda x: (str(x[0]), str(x[1])))
    idx = {c: 0 for c in cells_sorted}
    progressed = True
    while len(chosen) < cap and progressed:
        progressed = False
        for c in cells_sorted:
            if len(chosen) >= cap:
                break
            lst = by_cell[c]
            while idx[c] < len(lst):
                t = lst[idx[c]]; idx[c] += 1
                if t not in chosen_set:
                    chosen.append(t); chosen_set.add(t); progressed = True
                    break

    chosen = sorted(chosen)
    strata = {}
    for t in chosen:
        c = cell(results[t])
        key = f"dose={c[0]},break_side={c[1]}"
        strata[key] = strata.get(key, 0) + 1
    report = {
        "sample_task_ids": chosen,
        "n_sampled": len(chosen),
        "n_total": len(all_ids),
        "per_stratum_counts": strata,
        "n_forced_contaminated_or_defaulted": len([t for t in chosen
                                                   if contaminated(results[t]) or defaulted(results[t])]),
    }
    return chosen, report


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 Stage-2 GPU-path oracle: bounded stratified CPU cross-check")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path)
    ap.add_argument("--pruned", type=Path, default=Path("/dev/null"))
    ap.add_argument("--results-dir", required=True, type=Path, help="the GPU Stage-2 results/ dir")
    ap.add_argument("--sample-cap", type=int, default=12)
    ap.add_argument("--arms", default="B")
    ap.add_argument("--oracle-threads", type=int, default=1)
    ap.add_argument("--seed", type=int, default=20260716)
    args = ap.parse_args()

    results = load_results(args.results_dir)
    if not results:
        _log(f"[oracle-sample] no result files in {args.results_dir} — run the scored pass first")
        sys.exit(1)

    sample, strata = choose_sample(results, args.sample_cap)
    _log(f"[oracle-sample] chose {len(sample)}/{len(results)} tasks; strata={strata['per_stratum_counts']}; "
         f"forced(contam>0|defaulted)={strata['n_forced_contaminated_or_defaulted']}")

    # stage ONLY the sampled result files into a temp dir so oracle_verify's glob re-scores exactly them
    tmp = Path(tempfile.mkdtemp(prefix="stage2-oracle-"))
    try:
        for tid in sample:
            shutil.copy2(args.results_dir / f"{tid}.json", tmp / f"{tid}.json")

        # run oracle_verify.py UNCHANGED against the temp dir; frac=1.0 + single worker-sig → all N
        oracle_py = DRIVER / "oracle_verify.py"
        cmd = [
            sys.executable, "-u", str(oracle_py),
            "--tasks", str(args.tasks), "--gen-log", str(args.gen_log),
            "--pruned", str(args.pruned), "--out-dir", str(tmp),
            "--arms", args.arms, "--frac", "1.0",
            "--min-per-worker", str(len(sample)),
            "--oracle-threads", str(args.oracle_threads), "--seed", str(args.seed),
        ]
        _log("[oracle-sample] running oracle_verify (fresh CPU 1-thread) on the staged sample ...")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        oracle_rc = proc.returncode

        # read oracle_verify's emitted result from the temp dir, augment with disclosure, write to the
        # REAL results dir as _oracle_result.json (the §5 path the verdict plan reads)
        tmp_oracle = tmp / "_oracle_result.json"
        if not tmp_oracle.exists():
            _log("[oracle-sample] oracle_verify produced no _oracle_result.json — treating as FAIL")
            sys.exit(2)
        oracle_report = json.loads(tmp_oracle.read_text())
        oracle_report["gpu_path_note"] = (
            "gpu-path oracle = bounded stratified CPU cross-check. This is a FRESH-process, "
            "1-thread CPU per-task re-score (via the unmodified oracle_verify.py / frozen "
            "score_one_task) of a stratified SAMPLE of the GPU-scored results — NOT a full-corpus "
            "re-score, and NOT the multi-worker-corruption check the registered CPU-fleet oracle ran "
            "(the GPU path is a single MPS process). It verifies instrument identity per sampled task "
            "on fresh CPU. Batching/composition equivalence is covered separately by the mandatory "
            "batched_stage2_equiv gate (zero boolean flips). PASS here + PASS there = the GPU Stage-2 "
            "scores are trustworthy for §5."
        )
        oracle_report["sample_composition"] = strata
        oracle_report["sample_cap"] = args.sample_cap
        oracle_report["verified_at"] = _ts()

        out_path = args.results_dir / "_oracle_result.json"
        out_path.write_text(json.dumps(oracle_report, indent=2))
        _log("[oracle-sample] RESULT " + json.dumps({
            "verdict": oracle_report.get("verdict"),
            "n_sampled_tasks": oracle_report.get("n_sampled_tasks"),
            "n_mismatches": oracle_report.get("n_mismatches"),
            "wrote": str(out_path),
        }))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if oracle_rc != 0:
        _log("[oracle-sample] *** FAIL: oracle mismatch on the GPU Stage-2 sample. Axis verdict BLOCKED. "
             "Report to lead for diagnosis — do NOT auto-continue.")
        sys.exit(2)
    _log("[oracle-sample] PASS: fresh-CPU per-task re-score matches the GPU results on the sample.")


if __name__ == "__main__":
    main()
