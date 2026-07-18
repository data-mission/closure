"""Reproduce filter_stage's filter-report.json + pruned-items.json FROM a batched-scores.json.

The registered filter pipeline (filter_stage.py) does score_draws → adjudicate → emits pruned-items.json
+ filter-report.json. The GPU batched filter pass (batched_scorer.py) emits only batched-scores.json
(raw per-(fam,state,draw,item) {raw, assert}). Stage-2 scoring's --pruned input needs pruned-items.json,
which the batched pass never produced. This tool closes that gap: it reconstructs score_draws's
{fam: {item: {"a":[bool...],"c":[bool...]}}} structure from the batched scores, then calls the FROZEN
filter_stage.adjudicate VERBATIM (imported, not re-implemented) to get the identical pruned set +
pass/exclude verdicts, and writes both files in filter_stage's exact shapes.

WHY THIS IS EXACT (not an approximation): score_draws (filter_stage.py:111-139) produces per-item
assertion BOOLEANS; batched_scorer emits the SAME booleans (its equivalence to the per-call frozen path
is gated by batched_equiv). adjudicate (filter_stage.py:143-193) is a PURE function of those booleans —
so feeding batched booleans through the frozen adjudicate yields the frozen report, IFF the batched
booleans equal the frozen booleans (guaranteed by the filter batched_equiv gate). This tool adds NO
scoring; it only re-shapes batched booleans and calls the frozen adjudicate.

TRAPS honored:
- must_change ONLY: score_draws/adjudicate operate on must_change; must_persist is never pruned and
  never enters this report (filter_stage.py:128 mc = task["must_change"]).
- correction_keep_cap: the FROZEN value is adjudicate's DEFAULT ARG = 2 (filter_stage.py:143); main
  calls adjudicate(top, scored, args.n_draws) with NO cap override (filter_stage.py:241) and the value
  is NOT in closure_harness config. This tool therefore calls the frozen adjudicate with its default
  (does not pass a cap), so the cap tracks the frozen source exactly. --correction-keep-cap is exposed
  ONLY for a hypothetical future frozen change; leaving it unset uses the frozen default. (Reported to
  lead: the brief said "read from config", but there is no config field — the frozen value lives in the
  default arg. Following the frozen source, as instructed on any discrepancy.)
- draw ORDER: score_draws appends a bool per PRESENT draw in d=0..n_draws order, skipping missing gens
  (g is None → continue). This tool reconstructs the a/c lists in the same d order from the batched
  scores, so list lengths (a_n/c_n) and majority() inputs match exactly.

CLI:
  cd ~/repos/closure/harness && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    uv run python -u ~/e8-driver/filter_report_from_batched.py \
      --tasks <corpus-candidates/<axis>.jsonl> --batched-scores ~/e8-run/<axis>-filter/batched-scores.json \
      --out-dir ~/e8-run/<axis>-filter --n-draws 3
Writes <out-dir>/pruned-items.json and <out-dir>/filter-report.json (filter_stage's exact shapes).
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
import filter_stage  # noqa: E402  (top_level_per_family + adjudicate — imported VERBATIM)
from common import atomic_write_json  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def load_batched_scores(path: Path) -> dict:
    """Load batched_scorer's output. Returns {(fam, state, draw, item): bool_assert}.

    batched-scores.json shape: {"scores": {"<fam>||<state>||<draw>||<item>": {"raw":..,"assert":bool}},
    "meta": {...}} (batched_scorer._score_all_shape). We consume ONLY the boolean assert per key —
    score_draws keeps only the boolean (filter_stage.py:137), so the raw float is irrelevant here."""
    obj = json.loads(path.read_text())
    scores = obj.get("scores", obj)  # tolerate a bare scores dict
    out = {}
    for k, v in scores.items():
        fam, state, draw, item = k.split("||")
        out[(fam, state, int(draw), int(item))] = bool(v["assert"])
    return out, obj.get("meta", {})


def reconstruct_scored(top: dict, batched: dict, n_draws: int) -> dict:
    """Rebuild score_draws's return shape {fam: {item_idx: {"a":[bool...],"c":[bool...]}}} from the
    batched per-(fam,state,draw,item) booleans, mirroring filter_stage.py:127-138 exactly:
      - per family, per must_change item, per state (assumption→'a', correction→'c'):
        append the boolean for each PRESENT draw in d=0..n_draws-1 order (skip missing, like g is None).
    A draw is 'present' iff the batched scores contain a key for (fam, state, d, item). Because
    batched_scorer emits a key for every (fam,state,draw,item) whose gen existed, presence here == gen
    presence there."""
    out = {}
    for fam, task in top.items():
        mc = task["must_change"]
        per_item = {i: {"a": [], "c": []} for i in range(len(mc))}
        for state, key in (("assumption", "a"), ("correction", "c")):
            for d in range(n_draws):
                # a draw is present iff item 0 has a key (all items of a present draw are emitted
                # together in score_draws' inner loop; presence is per-(fam,state,draw), not per-item)
                if (fam, state, d, 0) not in batched and len(mc) > 0:
                    # confirm truly absent (defensive: check any item index, not just 0)
                    if not any((fam, state, d, i) in batched for i in range(len(mc))):
                        continue
                for i in range(len(mc)):
                    b = batched.get((fam, state, d, i))
                    if b is None:
                        # a present draw must have ALL items scored (score_draws scores every item of
                        # a present gen); a hole here means a corrupt/partial batched file — fail loud
                        raise ValueError(
                            f"batched scores missing item {i} for present draw ({fam},{state},{d}); "
                            "partial/corrupt batched-scores.json — refuse to build a wrong report")
                    per_item[i][key].append(bool(b))
        out[fam] = per_item
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Rebuild filter-report.json + pruned-items.json from batched scores")
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--batched-scores", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--n-draws", type=int, default=3)
    ap.add_argument("--families", type=str, default=None,
                    help="restrict to comma-separated family ids (e.g. the smoke families)")
    ap.add_argument("--correction-keep-cap", type=int, default=None,
                    help="ONLY for a hypothetical future frozen change; unset = frozen adjudicate "
                         "default (2). Leave unset to track the frozen source exactly.")
    args = ap.parse_args()

    from closure_harness.config import CONFIG, config_hash
    CH = config_hash()
    threshold = CONFIG.outcome.assert_threshold

    tasks = [json.loads(l) for l in args.tasks.read_text().splitlines() if l.strip()]
    top = filter_stage.top_level_per_family(tasks)  # frozen family selection (filter_stage.py:41)
    if args.families:
        keep = set(args.families.split(","))
        top = {f: t for f, t in top.items() if f in keep}

    batched, meta = load_batched_scores(args.batched_scores)
    _log(f"[report] {len(top)} families, threshold={threshold}, "
         f"batched keys={len(batched)}, batched device={meta.get('device')}")

    t0 = time.time()
    scored = reconstruct_scored(top, batched, args.n_draws)

    # FROZEN adjudicate — imported verbatim (filter_stage.py:143-193). Pass the cap only if the caller
    # explicitly overrode it; otherwise use the frozen DEFAULT (=2) by not passing the kwarg.
    if args.correction_keep_cap is None:
        passed, excluded, pruned_rows, per_family = filter_stage.adjudicate(top, scored, args.n_draws)
    else:
        passed, excluded, pruned_rows, per_family = filter_stage.adjudicate(
            top, scored, args.n_draws, correction_keep_cap=args.correction_keep_cap)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    # pruned-items.json — EXACT filter_stage.main output (the list of pruned_rows, filter_stage.py:244)
    atomic_write_json(args.out_dir / "pruned-items.json", pruned_rows)

    # filter-report.json — EXACT filter_stage.main shape (filter_stage.py:245-267), including the
    # ruling_confirmations block (verbatim from the frozen main) and elapsed_s.
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
    _log("[report] " + json.dumps({k: report[k] for k in
         ("n_families", "n_passed", "n_excluded", "n_pruned_items")}))
    _log(f"[report] wrote pruned-items.json ({len(pruned_rows)} rows) + filter-report.json "
         f"→ {args.out_dir}")


if __name__ == "__main__":
    main()
