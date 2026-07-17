"""E8 A-dependency FILTER — registered two-state × three-draw filter, per family TOP LEVEL.

Registered pre-freeze exclusion filter (E5 §8/§9 rule, carried to E8; manager filter ruling
task #24 prep). For each FAMILY, on its TOP-LEVEL record only (6 API draws/family):
  1. GENERATE 3 draws in the ASSUMPTION (A) state (correction docs withheld — per-axis, via
     axis_prompt.documents_for_state) and 3 in the full CORRECTION state, all through the SAME
     frozen ARM-B pipeline + rate limiter (generation_driver machinery).
  2. SCORE every draw's must_change conclusions via the FROZEN path (_still_asserts at the frozen
     assert_threshold — the same per-item scoring the scorer uses).
  3. FILTER RULE (E5): a family PASSES iff its must_change conclusions genuinely FLIP between
     states — i.e. the A-state asserts them (pre-correction world) and the correction-state does
     not. Operationalized per the E5 pilot: a must_change item is A-DEPENDENT iff it is asserted
     in the A-state AND flips (drops) under correction. A family with NO A-dependent must_change
     item is EXCLUDED (its "correction" changes nothing measurable).
  4. PRUNING REGISTER: drop any must_change conclusion still asserted in >= 2 of the 3
     CORRECTION-state draws (E5 pruning rule: a conclusion the corrected model keeps re-asserting
     is not a clean contamination target). Emitted as pruned-items.json — the scoring stage's
     --pruned input.
  5. EXCLUSIONS counted + reported per the registration (excluded families never enter the run).

Zero spend until launched with a key; --dry-run uses the fake generator. Scoring is the frozen
path verbatim. A-state prompt withhold rules are per-axis (axis_prompt) and were confirmed against
the real corpora; any ambiguous withhold is flagged, not guessed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

DRIVER = Path(__file__).resolve().parent
sys.path.insert(0, str(DRIVER))
from common import append_jsonl, atomic_write_json, load_jsonl, set_cpu_threads  # noqa: E402
from axis_prompt import build_prompt  # noqa: E402


# --------------------------------------------------------------------------- family top-levels
def top_level_per_family(tasks: list[dict]) -> dict[str, dict]:
    """One record per family: the TOP dose level (max dose_level, int-canon; string fallback)."""
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        by_fam[t.get("family_id", t["task_id"])].append(t)

    def dose_key(t):
        dl = t.get("dose_level")
        if isinstance(dl, int):
            return dl
        if isinstance(dl, str):  # "D3"/"C2" → trailing int
            digits = "".join(ch for ch in dl if ch.isdigit())
            return int(digits) if digits else 0
        return 0

    return {fam: max(recs, key=dose_key) for fam, recs in by_fam.items()}


# --------------------------------------------------------------------------- generation (2 states × 3)
def run_filter_generation(top: dict[str, dict], gen_log: Path, template: str, arm_b: str,
                          provider, config_hash: str, n_draws: int, rate, max_retries,
                          backoff_base) -> None:
    """Generate n_draws per (family, state). Resumable: skips (family, state, draw) already banked.

    Draw rows are tagged with `filter_state` ("assumption"|"correction") and `draw_index` so the
    scorer/analysis can separate them. Uses generation_driver.generate_one for the frozen guards.
    """
    from generation_driver import TokenBucket, generate_one
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    banked = set()
    for r in load_jsonl(gen_log):
        if r.get("config_hash") == config_hash and not r.get("error"):
            banked.add((r["task_id"], r.get("filter_state"), r.get("draw_index")))

    jobs = []
    for fam, task in top.items():
        for state in ("assumption", "correction"):
            for d in range(n_draws):
                if (task["task_id"], state, d) in banked:
                    continue
                jobs.append((task, state, d))
    print(f"[filter-gen] {len(jobs)} draws to do "
          f"({len(top)} families × 2 states × {n_draws} draws) ...", flush=True)

    bucket = TokenBucket(rate)
    log_lock = threading.Lock()

    def work(job):
        task, state, d = job
        prompt = build_prompt(task, "B", arm_b, template, state=state)
        bucket.acquire()
        row = generate_one(provider, task, "B", prompt, config_hash, max_retries, backoff_base)
        row["filter_state"] = state
        row["draw_index"] = d
        with log_lock:
            append_jsonl(gen_log, row)
        return "error" in row

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, j) for j in jobs]
        n = 0
        for f in as_completed(futs):
            n += 1
            if n % 20 == 0:
                print(f"[filter-gen]   {n}/{len(jobs)}", flush=True)


# --------------------------------------------------------------------------- scoring both states
def score_draws(top: dict[str, dict], gen_log: Path, threshold: float,
                config_hash: str, n_draws: int):
    """For each family, return per-must_change-item assertion across A-state and correction-state
    draws. Uses the frozen _still_asserts. Returns {family_id: {item_idx: {"a":[bool×k],"c":[bool×k]}}}."""
    from closure_harness.nli import NLIScorer
    from closure_harness.schema import parse_output
    from closure_harness.outcomes import _still_asserts

    # index generations: (task_id, state, draw) -> output
    gens: dict[tuple, dict] = {}
    for r in load_jsonl(gen_log):
        if r.get("config_hash") == config_hash and not r.get("error") and "filter_state" in r:
            gens[(r["task_id"], r["filter_state"], r["draw_index"])] = r["output"]

    scalar = NLIScorer()
    out: dict[str, dict] = {}
    for fam, task in top.items():
        mc = task["must_change"]
        per_item = {i: {"a": [], "c": []} for i in range(len(mc))}
        for state, key in (("assumption", "a"), ("correction", "c")):
            for d in range(n_draws):
                g = gens.get((task["task_id"], state, d))
                if g is None:
                    continue
                o = parse_output(g)
                for i, concl in enumerate(mc):
                    per_item[i][key].append(bool(_still_asserts(scalar, o, concl, threshold)))
        out[fam] = per_item
    return out


# --------------------------------------------------------------------------- filter + pruning
def adjudicate(top: dict[str, dict], scored: dict, n_draws: int, correction_keep_cap: int = 2):
    """Apply the E5 filter rule + build the pruning register.

    A must_change item i is A-DEPENDENT iff it is asserted in a MAJORITY of A-state draws AND NOT
    asserted in a majority of correction-state draws (it flips). A family with >=1 A-dependent item
    PASSES; a family with 0 is EXCLUDED (correction changes nothing measurable).

    PRUNING: item i is pruned iff asserted in >= correction_keep_cap (default 2) of 3 correction
    draws — the corrected model keeps re-asserting it, so it's not a clean contamination target.
    Emits pruned-items.json rows {task_id, item_index} for the scorer's --pruned input.
    """
    def majority(bools):
        return sum(bools) > len(bools) / 2 if bools else False

    passed, excluded, pruned_rows = [], [], []
    per_family = {}
    for fam, task in top.items():
        items = scored[fam]
        a_dependent = []
        pruned_here = []
        for i, ac in items.items():
            a_maj = majority(ac["a"])
            c_maj = majority(ac["c"])
            flips = a_maj and not c_maj
            if flips:
                a_dependent.append(i)
            # pruning candidate: still asserted in >= cap of the correction draws
            if sum(ac["c"]) >= correction_keep_cap:
                pruned_here.append(i)
        family_passes = len(a_dependent) > 0
        (passed if family_passes else excluded).append(fam)
        # Emit pruning rows ONLY for families that PASS the filter — excluded families never enter
        # the scoring stage, so pruning their items would put dead entries in the register the
        # scorer consumes. Pruning applies to the tasks that will actually be scored.
        if family_passes:
            for i in pruned_here:
                ac = items[i]
                pruned_rows.append({"task_id": task["task_id"], "item_index": i,
                                    "family_id": fam,
                                    "reason": f"asserted in {sum(ac['c'])}/{len(ac['c'])} "
                                              "correction draws (>= cap)"})
        per_family[fam] = {
            "task_id": task["task_id"], "axis": task.get("axis"),
            "n_must_change": len(items),
            "a_dependent_items": a_dependent, "pruned_items": pruned_here,
            "passes": family_passes,
            "assertion_counts": {i: {"a": sum(ac["a"]), "c": sum(ac["c"]),
                                     "a_n": len(ac["a"]), "c_n": len(ac["c"])}
                                 for i, ac in items.items()},
        }
    return passed, excluded, pruned_rows, per_family


def main() -> None:
    ap = argparse.ArgumentParser(description="E8 A-dependency filter (2 states × 3 draws / family)")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--gen-log", required=True, type=Path, help="filter draw log (separate)")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--arm-b-instruction", type=Path, required=True)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--rate", type=float, default=2.0)
    ap.add_argument("--max-retries", type=int, default=5)
    ap.add_argument("--backoff-base", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-unpinned-instruction", action="store_true")
    args = ap.parse_args()

    set_cpu_threads(args.threads)
    from closure_harness.config import CONFIG, config_hash
    import hashlib
    CH = config_hash()
    threshold = CONFIG.outcome.assert_threshold
    template = args.template.read_text()

    # instruction hash pin (same rule as generation_driver)
    ARMB_PINNED = "f9c242958fccba4eb536ef74d903f6c897545f4365211a6dacd00b6fdbe70a7c"
    armb_bytes = args.arm_b_instruction.read_bytes()
    if hashlib.sha256(armb_bytes).hexdigest() != ARMB_PINNED and not args.allow_unpinned_instruction:
        raise SystemExit("ARM-B instruction hash mismatch; refusing (see generation_driver).")
    arm_b = " ".join(l[2:].strip() for l in armb_bytes.decode().splitlines() if l.startswith("> "))

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = top_level_per_family(tasks)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        from generation_driver import make_fake_provider
        provider = make_fake_provider(CONFIG.generation.model_pin)
    else:
        from closure_harness.providers import make_provider
        provider = make_provider()

    t0 = time.time()
    run_filter_generation(top, args.gen_log, template, arm_b, provider, CH,
                          args.n_draws, args.rate, args.max_retries, args.backoff_base)
    scored = score_draws(top, args.gen_log, threshold, CH, args.n_draws)
    passed, excluded, pruned_rows, per_family = adjudicate(top, scored, args.n_draws)

    # emit the pruning register (scorer's --pruned input) and the filter report
    atomic_write_json(args.out_dir / "pruned-items.json", pruned_rows)
    report = {
        "stage": "A-dependency-filter", "config_hash": CH,
        # Withhold-rule confirmations recorded in the run record (manager ruling 2026-07-17):
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
    print("[filter] RESULT " + json.dumps({k: report[k] for k in
          ("n_families", "n_passed", "n_excluded", "n_pruned_items")}), flush=True)
    print(f"[filter] wrote pruned-items.json ({len(pruned_rows)} rows) + filter-report.json",
          flush=True)


if __name__ == "__main__":
    main()
